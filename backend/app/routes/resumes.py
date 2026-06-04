import logging
import uuid
from datetime import datetime, timedelta, timezone

from arq import create_pool as arq_create_pool
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
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
from app.models.job import Job
from app.models.resume import Resume
from app.schemas.resume import (
    ResumeGenerateManualRequest,
    ResumeGenerateRequest,
    ResumeGenerateResponse,
    ResumeListItem,
    ResumeListResponse,
    ResumeResponse,
    ResumeStatusResponse,
)
from app.services.document_assets import (
    delete_resume_s3_assets,
    load_resume_text_from_s3_key,
)
from app.services.resume_text_extractor import extract_text_from_resume_bytes
from app.services.s3_storage import S3Storage, S3StorageError, upload_resume_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])

DEDUP_WINDOW_MINUTES = 5


def _get_redis_settings() -> RedisSettings:
    return redis_settings_from_url(app_settings.REDIS_URL)


async def _enqueue_resume_job(
    resume_id: str,
    user_id: str,
    profile_id: str,
    job_description: str,
    uploaded_resume_text: str | None = None,
    job_title: str = "",
    company_name: str = "",
) -> None:
    redis = await arq_create_pool(_get_redis_settings())
    await redis.enqueue_job(
        "generate_resume_job",
        resume_id,
        user_id,
        profile_id,
        job_description,
        uploaded_resume_text,
        job_title,
        company_name,
        _queue_name=QUEUE_AI,
    )
    await redis.close()


async def _load_profile_resume_text(profile: CandidateProfile) -> str | None:
    if not profile.resume_s3_key:
        return None
    text = await load_resume_text_from_s3_key(profile.resume_s3_key)
    return text if text.strip() else None


async def _replace_existing_job_resume(
    user_id: str,
    job_id: uuid.UUID,
    session: AsyncSession,
) -> Resume | None:
    result = await session.execute(
        select(Resume).where(Resume.user_id == user_id, Resume.job_id == job_id)
    )
    existing = result.scalar_one_or_none()
    if existing is None:
        return None
    await delete_resume_s3_assets(existing)
    await session.delete(existing)
    await session.commit()
    return existing


async def _find_in_progress_resume(
    user_id: str,
    job_id: uuid.UUID,
    session: AsyncSession,
) -> Resume | None:
    cutoff = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
    result = await session.execute(
        select(Resume).where(
            Resume.user_id == user_id,
            Resume.job_id == job_id,
            Resume.status == "generating",
            Resume.created_at > cutoff,
        )
    )
    return result.scalar_one_or_none()


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
            detail="Please complete onboarding before generating resumes.",
        )
    return profile


async def _check_ownership(resume: Resume, user: CurrentUser) -> None:
    if str(resume.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this resume.",
        )


@router.post("/generate", response_model=ResumeGenerateResponse)
@limiter.limit("5/minute")
async def generate_resume(
    request: Request,
    body: ResumeGenerateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeGenerateResponse:
    profile = await _resolve_profile(user.id, session)

    job_description: str | None = None
    job_id: uuid.UUID | None = body.job_id
    job_title: str | None = None
    company_name: str | None = None

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
    else:
        job_description = body.job_description

    uploaded_resume_text: str | None = None
    uploaded_resume_s3_key: str | None = None
    try:
        uploaded_resume_text = await _load_profile_resume_text(profile)
        uploaded_resume_s3_key = profile.resume_s3_key
    except S3StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to load uploaded resume: {exc}",
        ) from exc

    if job_id:
        in_progress = await _find_in_progress_resume(user.id, job_id, session)
        if in_progress:
            return ResumeGenerateResponse(
                resume_id=in_progress.id,
                status=in_progress.status or "generating",
            )

        if not body.force_regenerate:
            completed_result = await session.execute(
                select(Resume).where(
                    Resume.user_id == user.id,
                    Resume.job_id == job_id,
                    Resume.status == "completed",
                )
            )
            completed = completed_result.scalar_one_or_none()
            if completed:
                logger.info(
                    "resume_dedup_hit",
                    extra={
                        "user_id": str(user.id),
                        "job_id": str(job_id),
                        "resume_id": str(completed.id),
                    },
                )
                return ResumeGenerateResponse(
                    resume_id=completed.id,
                    status="completed",
                    ats_score=completed.ats_score,
                    content_json=completed.content_json,
                )
        else:
            await _replace_existing_job_resume(user.id, job_id, session)

    resume = Resume(
        user_id=user.id,
        job_id=job_id,
        status="generating",
        uploaded_resume_s3_key=uploaded_resume_s3_key,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)

    try:
        await _enqueue_resume_job(
            str(resume.id),
            str(user.id),
            str(profile.id),
            job_description or "",
            uploaded_resume_text=uploaded_resume_text,
            job_title=job_title or "",
            company_name=company_name or "",
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"resume_id": str(resume.id)})
        resume.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start resume generation. Please try again.",
        )

    logger.info(
        "resume_generation_enqueued",
        extra={
            "user_id": str(user.id),
            "job_id": str(job_id) if job_id else None,
            "candidate_profile_id": str(profile.id),
            "resume_id": str(resume.id),
        },
    )

    return ResumeGenerateResponse(
        resume_id=resume.id,
        status="generating",
    )


@router.post("/generate-manual", response_model=ResumeGenerateResponse)
@limiter.limit("5/minute")
async def generate_resume_manual(
    request: Request,
    body: ResumeGenerateManualRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeGenerateResponse:
    profile = await _resolve_profile(user.id, session)

    resume = Resume(
        user_id=user.id,
        job_id=None,
        status="generating",
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)

    try:
        await _enqueue_resume_job(str(resume.id), str(user.id), str(profile.id), body.job_description)
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"resume_id": str(resume.id)})
        resume.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start resume generation. Please try again.",
        )

    logger.info(
        "resume_generation_manual_enqueued",
        extra={
            "user_id": str(user.id),
            "candidate_profile_id": str(profile.id),
            "resume_id": str(resume.id),
            "description_length": len(body.job_description),
        },
    )

    return ResumeGenerateResponse(
        resume_id=resume.id,
        status="generating",
    )


@router.get("/{resume_id}/status", response_model=ResumeStatusResponse)
async def get_resume_status(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeStatusResponse:
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    await _check_ownership(resume, user)

    return ResumeStatusResponse(
        resume_id=resume.id,
        status=resume.status or "generating",
        progress_step=None,
        ats_score=resume.ats_score,
    )


@router.get("", response_model=ResumeListResponse)
async def list_resumes(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeListResponse:
    # Deferred column loading: only fetch columns needed for list display
    stmt = (
        select(
            Resume.id,
            Resume.job_id,
            Resume.ats_score,
            Resume.created_at,
            Job.title.label("job_title"),
            Job.company.label("company_name"),
        )
        .outerjoin(Job, Resume.job_id == Job.id)
        .where(Resume.user_id == user.id)
        .order_by(desc(Resume.created_at))
        .limit(limit)
        .offset(offset)
    )
    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = (
        select(func.count())
        .select_from(Resume)
        .where(Resume.user_id == user.id)
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    resumes = [
        ResumeListItem(
            id=row.id,
            job_id=row.job_id,
            job_title=row.job_title,
            company_name=row.company_name,
            ats_score=row.ats_score,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return ResumeListResponse(resumes=resumes, total=total)


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeResponse:
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    await _check_ownership(resume, user)

    job_title: str | None = None
    company_name: str | None = None
    if resume.job_id:
        job_result = await session.execute(
            select(Job).where(Job.id == resume.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job_title = job.title
            company_name = job.company

    if resume.status == "generating":
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Resume is still being generated.",
        )

    return ResumeResponse(
        id=resume.id,
        job_id=resume.job_id,
        job_title=job_title,
        company_name=company_name,
        ats_score=resume.ats_score,
        ats_breakdown=resume.ats_breakdown,
        content_json=resume.content_json,
        pdf_url=resume.pdf_url,
        created_at=resume.created_at,
        updated_at=resume.updated_at,
        status=resume.status,
    )


@router.get("/{resume_id}/pdf")
async def download_resume_pdf(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
):
    result = await session.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    await _check_ownership(resume, user)
    if not resume.pdf_s3_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF not available for this resume.",
        )
    try:
        storage = S3Storage()
        url = await storage.get_presigned_url(resume.pdf_s3_key)
        resume.pdf_url = url
        session.add(resume)
        await session.commit()
        return RedirectResponse(url=url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    except S3StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to generate download URL: {exc}",
        ) from exc


@router.post("/generate-with-upload", response_model=ResumeGenerateResponse)
@limiter.limit("5/minute")
async def generate_resume_with_upload(
    request: Request,
    job_id: uuid.UUID = Form(...),
    force_regenerate: bool = Form(False),
    resume_file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ResumeGenerateResponse:
    profile = await _resolve_profile(user.id, session)
    job_result = await session.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    max_bytes = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await resume_file.read(max_bytes + 1)
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large. Maximum size is {app_settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    filename = resume_file.filename or "resume.pdf"
    uploaded_resume_text = extract_text_from_resume_bytes(content, filename)
    per_job_key = upload_resume_key(f"{user.id}/jobs/{job_id}", filename)
    try:
        storage = S3Storage()
        content_type = (
            "application/pdf"
            if filename.lower().endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        await storage.upload_file(content, per_job_key, content_type)
    except S3StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to store resume: {exc}",
        ) from exc

    if force_regenerate:
        await _replace_existing_job_resume(user.id, job_id, session)
    else:
        in_progress = await _find_in_progress_resume(user.id, job_id, session)
        if in_progress:
            return ResumeGenerateResponse(
                resume_id=in_progress.id,
                status=in_progress.status or "generating",
            )
        completed_result = await session.execute(
            select(Resume).where(
                Resume.user_id == user.id,
                Resume.job_id == job_id,
                Resume.status == "completed",
            )
        )
        completed = completed_result.scalar_one_or_none()
        if completed:
            return ResumeGenerateResponse(
                resume_id=completed.id,
                status="completed",
                ats_score=completed.ats_score,
                content_json=completed.content_json,
            )

    resume = Resume(
        user_id=user.id,
        job_id=job_id,
        status="generating",
        uploaded_resume_s3_key=per_job_key,
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)

    try:
        await _enqueue_resume_job(
            str(resume.id),
            str(user.id),
            str(profile.id),
            job.description or "",
            uploaded_resume_text=uploaded_resume_text,
            job_title=job.title,
            company_name=job.company,
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"resume_id": str(resume.id)})
        resume.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start resume generation. Please try again.",
        )

    return ResumeGenerateResponse(resume_id=resume.id, status="generating")


@router.delete("/{resume_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resume(
    resume_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    result = await session.execute(
        select(Resume).where(Resume.id == resume_id)
    )
    resume = result.scalar_one_or_none()
    if resume is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found.",
        )
    await _check_ownership(resume, user)

    await delete_resume_s3_assets(resume)
    await session.delete(resume)
    await session.commit()

    logger.info(
        "resume_deleted",
        extra={"resume_id": str(resume_id), "user_id": str(user.id)},
    )
