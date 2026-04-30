import logging
import os
import uuid

from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.database import get_async_session
from app.models.application import Application
from app.models.base import ApplicationStatus
from app.models.job import Job
from app.schemas.apply import (
    ATSDetectRequest,
    ATSDetectResponse,
    ATSDetectionStatusResponse,
)

logger = logging.getLogger(__name__)

apply_router = APIRouter(prefix="/api/apply", tags=["apply"])


def _get_redis_settings() -> RedisSettings:
    url = settings.REDIS_URL
    host = url.split("@")[-1].split(":")[0] if "@" in url else "localhost"
    port = int(url.split(":")[-1].split("/")[0]) if ":" in url else 6379
    database = int(url.rstrip("/").split("/")[-1]) if "/" in url else 0
    return RedisSettings(host=host, port=port, database=database)


@apply_router.post("/detect", response_model=ATSDetectResponse)
async def detect_ats(
    request: ATSDetectRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ATSDetectResponse:
    result = await session.execute(select(Job).where(Job.id == request.job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    apply_url = request.apply_url or job.apply_url
    if not apply_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job has no apply URL.",
        )

    app_result = await session.execute(
        select(Application).where(
            Application.user_id == user.id,
            Application.job_id == request.job_id,
        )
    )
    application = app_result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Save the job first before detecting ATS.",
        )

    if application.status == ApplicationStatus.generating:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Detection already in progress.",
        )

    application.status = ApplicationStatus.generating
    session.add(application)
    await session.commit()

    try:
        redis = await arq_create_pool(_get_redis_settings())
        arq_job = await redis.enqueue_job(
            "ats_detect_job",
            str(application.id),
            str(user.id),
            apply_url,
            _job_id=f"ats_detect_{application.id}",
        )
        await redis.close()
    except Exception as exc:
        logger.error(f"Failed to enqueue ATS detection: {exc}")
        application.status = ApplicationStatus.saved
        session.add(application)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start ATS detection.",
        )

    logger.info(
        "ats_detect_enqueued",
        extra={
            "application_id": str(application.id),
            "user_id": str(user.id),
            "job_id": str(request.job_id),
            "apply_url": apply_url,
        },
    )

    return ATSDetectResponse(
        application_id=application.id,
        task_id=arq_job.job_id if arq_job else "",
        message="ATS detection started",
    )


@apply_router.get("/detect/{application_id}/status", response_model=ATSDetectionStatusResponse)
async def get_detection_status(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ATSDetectionStatusResponse:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    if application.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized.",
        )

    return ATSDetectionStatusResponse(
        application_id=application.id,
        job_id=application.job_id,
        status=application.status.value if isinstance(application.status, ApplicationStatus) else str(application.status),
        ats_platform=application.ats_platform,
        ats_detection_method=application.ats_detection_method,
        ats_confidence=application.ats_confidence,
        ats_form_url=application.ats_form_url,
        ats_detected_fields=application.ats_detected_fields,
        ats_screenshot_path=application.ats_screenshot_path,
        ats_detection_error=application.ats_detection_error,
        ats_difficulty=application.ats_difficulty,
    )


@apply_router.get("/detect/{application_id}/screenshot")
async def get_detection_screenshot(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> FileResponse:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )

    if application.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized.",
        )

    if not application.ats_screenshot_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot not available.",
        )

    screenshot_path = application.ats_screenshot_path
    resolved = os.path.realpath(screenshot_path)
    screenshot_dir = os.path.realpath(settings.ATS_SCREENSHOT_DIR)

    if not resolved.startswith(screenshot_dir):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied.",
        )

    if not os.path.isfile(resolved):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Screenshot file not found.",
        )

    return FileResponse(resolved, media_type="image/png")
