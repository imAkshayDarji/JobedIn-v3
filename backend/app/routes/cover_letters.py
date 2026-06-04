import logging
import uuid
from datetime import datetime, timedelta

from arq import create_pool as arq_create_pool
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings as app_settings
from app.services.redis_pool import QUEUE_AI, RedisSettings, redis_settings_from_url
from app.database import get_async_session
from app.middleware.rate_limit import limiter
from app.models.candidate import CandidateProfile
from app.models.cover_letter import CoverLetter
from app.models.job import Job
from app.models.resume import Resume
from app.services.document_assets import delete_cover_letter_s3_assets
from app.services.s3_storage import S3Storage, S3StorageError
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
    return redis_settings_from_url(app_settings.REDIS_URL)


async def _enqueue_cover_letter_job(
    cover_letter_id: str,
    user_id: str,
    profile_id: str,
    job_description: str,
    tone: str = "professional",
    generated_resume_json: dict | None = None,
    job_title: str = "",
    company_name: str = "",
) -> None:
    redis = await arq_create_pool(_get_redis_settings())
    await redis.enqueue_job(
        "generate_cover_letter_job",
        cover_letter_id,
        user_id,
        profile_id,
        job_description,
        tone,
        generated_resume_json,
        job_title,
        company_name,
        _queue_name=QUEUE_AI,
    )
    await redis.close()


async def _load_job_resume_json(
    user_id: str,
    job_id: uuid.UUID,
    session: AsyncSession,
) -> tuple[dict | None, str, str]:
    result = await session.execute(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.job_id == job_id,
            Resume.status == "completed",
        )
    )
    resume = result.scalar_one_or_none()
    if resume is None or not resume.content_json:
        return None, "", ""
    job_title = ""
    company_name = ""
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job:
        job_title = job.title
        company_name = job.company
    return resume.content_json, job_title, company_name


async def _resolve_profile(
    user_id: str, session: AsyncSession
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
    job_title: str | None = None
    company_name: str | None = None
    generated_resume_json: dict | None = None

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
        job_title = job.title
        company_name = job.company
        generated_resume_json, resume_job_title, resume_company = await _load_job_resume_json(
            user.id, job_id, session
        )
        if not job_title:
            job_title = resume_job_title
        if not company_name:
            company_name = resume_company
    else:
        job_description = body.job_description

    if job_id and generated_resume_json is None and not body.force_regenerate:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Generate a resume for this job before creating a cover letter.",
        )

    if job_id:
        cutoff = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        in_progress_result = await session.execute(
            select(CoverLetter).where(
                CoverLetter.user_id == user.id,
                CoverLetter.job_id == job_id,
                CoverLetter.status == "generating",
                CoverLetter.created_at > cutoff,
            )
        )
        in_progress = in_progress_result.scalar_one_or_none()
        if in_progress:
            return CoverLetterGenerateResponse(
                cover_letter_id=in_progress.id,
                status=in_progress.status or "generating",
            )

        if not body.force_regenerate:
            completed_result = await session.execute(
                select(CoverLetter).where(
                    CoverLetter.user_id == user.id,
                    CoverLetter.job_id == job_id,
                    CoverLetter.status == "completed",
                )
            )
            existing = completed_result.scalar_one_or_none()
            if existing:
                logger.info(
                    "cover_letter_dedup_hit",
                    extra={
                        "user_id": str(user.id),
                        "job_id": str(job_id),
                        "cover_letter_id": str(existing.id),
                    },
                )
                return CoverLetterGenerateResponse(
                    cover_letter_id=existing.id,
                    status="completed",
                    content_json=existing.content_json,
                )
        else:
            old_result = await session.execute(
                select(CoverLetter).where(
                    CoverLetter.user_id == user.id,
                    CoverLetter.job_id == job_id,
                )
            )
            for old in old_result.scalars().all():
                await delete_cover_letter_s3_assets(old)
                await session.delete(old)
            await session.commit()

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
            str(cover_letter.id),
            str(user.id),
            str(profile.id),
            job_description,
            tone,
            generated_resume_json=generated_resume_json,
            job_title=job_title or "",
            company_name=company_name or "",
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
        pdf_url=cover_letter.pdf_url,
        tone=cover_letter.tone,
        ai_model_used=cover_letter.ai_model_used,
        status=cover_letter.status,
        created_at=cover_letter.created_at,
        updated_at=cover_letter.updated_at,
    )


@router.get("/{cover_letter_id}/pdf")
async def download_cover_letter_pdf(
    cover_letter_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
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
    if not cover_letter.pdf_s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this cover letter.",
        )
    try:
        storage = S3Storage()
        url = await storage.get_presigned_url(cover_letter.pdf_s3_key)
        cover_letter.pdf_url = url
        session.add(cover_letter)
        await session.commit()
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except S3StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate download URL: {exc}",
        ) from exc


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

    await delete_cover_letter_s3_assets(cover_letter)
    await session.delete(cover_letter)
    await session.commit()

    logger.info(
        "cover_letter_deleted",
        extra={"cover_letter_id": str(cover_letter_id), "user_id": str(user.id)},
    )
