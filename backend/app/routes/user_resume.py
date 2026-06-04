import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings as app_settings
from app.database import get_async_session
from app.models.candidate import CandidateProfile
from app.schemas.user_resume import UserResumeMetadataResponse, UserResumeUploadResponse
from app.services.resume_text_extractor import extract_text_from_resume_bytes
from app.services.s3_storage import S3Storage, S3StorageError, upload_resume_key

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/user", tags=["user-resume"])

TEXT_PREVIEW_LENGTH = 500


async def _resolve_profile(user_id: str, session: AsyncSession) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )
    return profile


def _validate_resume_file(filename: str | None, content_type: str | None) -> None:
    if not filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Filename is required",
        )
    lower = filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".docx")):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are accepted",
        )
    allowed_types = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if content_type and content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF and DOCX files are accepted",
        )


@router.post("/resume", response_model=UserResumeUploadResponse)
async def upload_user_resume(
    file: UploadFile,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserResumeUploadResponse:
    _validate_resume_file(file.filename, file.content_type)
    profile = await _resolve_profile(user.id, session)

    max_bytes = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
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

    extracted_text = extract_text_from_resume_bytes(content, file.filename or "resume.pdf")
    key = upload_resume_key(str(user.id), file.filename or "resume.pdf")

    try:
        storage = S3Storage()
        if profile.resume_s3_key:
            await storage.delete_file(profile.resume_s3_key)
        content_type = (
            "application/pdf"
            if (file.filename or "").lower().endswith(".pdf")
            else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        await storage.upload_file(content, key, content_type)
    except S3StorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to store resume: {exc}",
        ) from exc

    uploaded_at = datetime.now(timezone.utc)
    profile.resume_s3_key = key
    profile.resume_upload_filename = file.filename
    profile.resume_uploaded_at = uploaded_at
    session.add(profile)
    await session.commit()

    preview = extracted_text[:TEXT_PREVIEW_LENGTH] if extracted_text else None
    logger.info("user_resume_uploaded", extra={"user_id": str(user.id), "key": key})

    return UserResumeUploadResponse(
        filename=file.filename or "resume.pdf",
        uploaded_at=uploaded_at,
        text_preview=preview,
    )


@router.get("/resume", response_model=UserResumeMetadataResponse)
async def get_user_resume(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> UserResumeMetadataResponse:
    profile = await _resolve_profile(user.id, session)
    preview: str | None = None
    if profile.resume_s3_key:
        try:
            from app.services.document_assets import load_resume_text_from_s3_key

            text = await load_resume_text_from_s3_key(profile.resume_s3_key)
            preview = text[:TEXT_PREVIEW_LENGTH] if text else None
        except (S3StorageError, HTTPException):
            preview = None

    return UserResumeMetadataResponse(
        has_uploaded_resume=bool(profile.resume_s3_key),
        filename=profile.resume_upload_filename,
        uploaded_at=profile.resume_uploaded_at,
        text_preview=preview,
    )


@router.delete("/resume", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_resume(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    if profile.resume_s3_key:
        try:
            storage = S3Storage()
            await storage.delete_file(profile.resume_s3_key)
        except S3StorageError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete resume: {exc}",
            ) from exc

    profile.resume_s3_key = None
    profile.resume_upload_filename = None
    profile.resume_uploaded_at = None
    session.add(profile)
    await session.commit()
    logger.info("user_resume_deleted", extra={"user_id": str(user.id)})
