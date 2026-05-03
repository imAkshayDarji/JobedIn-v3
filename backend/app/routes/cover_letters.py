import logging
import uuid
from datetime import datetime, timedelta

from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings as app_settings
from app.database import get_async_session
from app.middleware.rate_limit import limiter
from app.models.candidate import CandidateProfile
from app.models.cover_letter import CoverLetter
from app.models.job import Job
from app.schemas.cover_letter import (
    CoverLetterGenerateManualRequest,
    CoverLetterGenerateRequest,
    CoverLetterGenerateResponse,
    CoverLetterListItem,
    CoverLetterListResponse,
    CoverLetterResponse,
    CoverLetterStatusResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cover-letters", tags=["cover-letters"])

DEDUP_WINDOW_MINUTES = 5


def _get_redis_settings() -> RedisSettings:
    url = app_settings.REDIS_URL
    host = url.split("@")[-1].split(":")[0] if "@" in url else "localhost"
    port = int(url.split(":")[-1].split("/")[0]) if ":" in url else 6379
    database = int(url.rstrip("/").split("/")[-1]) if "/" in url else 0
    return RedisSettings(host=host, port=port, database=database)


async def _enqueue_cover_letter_job(
    cover_letter_id: str,
    user_id: str,
    profile_id: str,
    job_description: str,
    tone: str = "professional",
) -> None:
    redis = await arq_create_pool(_get_redis_settings())
    await redis.enqueue_job(
        "generate_cover_letter_job",
        cover_letter_id,
        user_id,
        profile_id,
        job_description,
        tone,
    )
    await redis.close()


async def _resolve_profile(
    user_id: uuid.UUID, session: AsyncSession
) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )
    if not profile.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please complete onboarding before generating cover letters.",
        )
    return profile


async def _check_ownership(cover_letter: CoverLetter, user: CurrentUser) -> None:
    if str(cover_letter.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this cover letter.",
        )


@router.post("/generate", response_model=CoverLetterGenerateResponse)
@limiter.limit("5/minute")
async def generate_cover_letter(
    request: Request,
    body: CoverLetterGenerateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CoverLetterGenerateResponse:
    profile = await _resolve_profile(user.id, session)

    job_description: str | None = None
    job_id: uuid.UUID | None = body.job_id

    if body.job_id:
        job_result = await session.execute(
            select(Job).where(Job.id == body.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )
        job_description = job.description or ""
    else:
        job_description = body.job_description

    # Dedup guard
    if job_id:
        cutoff = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        existing_result = await session.execute(
            select(CoverLetter).where(
                CoverLetter.user_id == user.id,
                CoverLetter.job_id == job_id,
                CoverLetter.created_at > cutoff,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing and existing.status == "completed":
            logger.info(
                "cover_letter_dedup_hit",
                extra={"user_id": str(user.id), "job_id": str(job_id), "cover_letter_id": str(existing.id)},
            )
            return CoverLetterGenerateResponse(
                cover_letter_id=existing.id,
                status="completed",
                content_json=existing.content_json,
            )

    tone = body.tone or "professional"
    cover_letter = CoverLetter(
        user_id=user.id,
        job_id=job_id,
        job_description=job_description if not job_id else None,
        tone=tone,
        status="generating",
    )
    session.add(cover_letter)
    await session.commit()
    await session.refresh(cover_letter)

    try:
        await _enqueue_cover_letter_job(
            str(cover_letter.id), str(user.id), str(profile.id), job_description, tone
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"cover_letter_id": str(cover_letter.id)})
        cover_letter.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start cover letter generation. Please try again.",
        )

    logger.info(
        "cover_letter_generation_enqueued",
        extra={
            "user_id": str(user.id),
            "job_id": str(job_id) if job_id else None,
            "candidate_profile_id": str(profile.id),
            "cover_letter_id": str(cover_letter.id),
            "tone": tone,
        },
    )

    return CoverLetterGenerateResponse(
        cover_letter_id=cover_letter.id,
        status="generating",
    )


@router.post("/generate-manual", response_model=CoverLetterGenerateResponse)
@limiter.limit("5/minute")
async def generate_cover_letter_manual(
    request: Request,
    body: CoverLetterGenerateManualRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CoverLetterGenerateResponse:
    profile = await _resolve_profile(user.id, session)

    tone = body.tone or "professional"
    cover_letter = CoverLetter(
        user_id=user.id,
        job_id=None,
        job_description=body.job_description,
        tone=tone,
        status="generating",
    )
    session.add(cover_letter)
    await session.commit()
    await session.refresh(cover_letter)

    try:
        await _enqueue_cover_letter_job(
            str(cover_letter.id), str(user.id), str(profile.id), body.job_description, tone
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"cover_letter_id": str(cover_letter.id)})
        cover_letter.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start cover letter generation. Please try again.",
        )

    logger.info(
        "cover_letter_generation_manual_enqueued",
        extra={
            "user_id": str(user.id),
            "candidate_profile_id": str(profile.id),
            "cover_letter_id": str(cover_letter.id),
            "description_length": len(body.job_description),
            "tone": tone,
        },
    )

    return CoverLetterGenerateResponse(
        cover_letter_id=cover_letter.id,
        status="generating",
    )


@router.get("/{cover_letter_id}/status", response_model=CoverLetterStatusResponse)
async def get_cover_letter_status(
    cover_letter_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CoverLetterStatusResponse:
    result = await session.execute(
        select(CoverLetter).where(CoverLetter.id == cover_letter_id)
    )
    cover_letter = result.scalar_one_or_none()
    if cover_letter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found.",
        )
    await _check_ownership(cover_letter, user)

    return CoverLetterStatusResponse(
        cover_letter_id=cover_letter.id,
        status=cover_letter.status or "generating",
        tone=cover_letter.tone,
    )


@router.get("", response_model=CoverLetterListResponse)
async def list_cover_letters(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CoverLetterListResponse:
    stmt = (
        select(
            CoverLetter.id,
            CoverLetter.job_id,
            CoverLetter.tone,
            CoverLetter.created_at,
            Job.title.label("job_title"),
            Job.company.label("company_name"),
        )
        .outerjoin(Job, CoverLetter.job_id == Job.id)
        .where(CoverLetter.user_id == user.id)
        .order_by(desc(CoverLetter.created_at))
        .limit(limit)
        .offset(offset)
    )
    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = (
        select(func.count())
        .select_from(CoverLetter)
        .where(CoverLetter.user_id == user.id)
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    cover_letters = [
        CoverLetterListItem(
            id=row.id,
            job_id=row.job_id,
            job_title=row.job_title,
            company_name=row.company_name,
            tone=row.tone,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return CoverLetterListResponse(cover_letters=cover_letters, total=total)


@router.get("/{cover_letter_id}", response_model=CoverLetterResponse)
async def get_cover_letter(
    cover_letter_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CoverLetterResponse:
    result = await session.execute(
        select(CoverLetter).where(CoverLetter.id == cover_letter_id)
    )
    cover_letter = result.scalar_one_or_none()
    if cover_letter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found.",
        )
    await _check_ownership(cover_letter, user)

    job_title: str | None = None
    company_name: str | None = None
    if cover_letter.job_id:
        job_result = await session.execute(
            select(Job).where(Job.id == cover_letter.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job_title = job.title
            company_name = job.company

    if cover_letter.status == "generating":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Cover letter is still being generated.",
        )

    return CoverLetterResponse(
        id=cover_letter.id,
        job_id=cover_letter.job_id,
        job_title=job_title,
        company_name=company_name,
        content=cover_letter.content,
        content_json=cover_letter.content_json,
        tone=cover_letter.tone,
        ai_model_used=cover_letter.ai_model_used,
        status=cover_letter.status,
        created_at=cover_letter.created_at,
        updated_at=cover_letter.updated_at,
    )


@router.delete("/{cover_letter_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cover_letter(
    cover_letter_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    result = await session.execute(
        select(CoverLetter).where(CoverLetter.id == cover_letter_id)
    )
    cover_letter = result.scalar_one_or_none()
    if cover_letter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cover letter not found.",
        )
    await _check_ownership(cover_letter, user)

    await session.delete(cover_letter)
    await session.commit()

    logger.info(
        "cover_letter_deleted",
        extra={"cover_letter_id": str(cover_letter_id), "user_id": str(user.id)},
    )
