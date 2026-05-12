import asyncio
import json
import logging
import os
import uuid

from arq import create_pool as arq_create_pool
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import FileResponse, StreamingResponse
from slowapi.util import get_remote_address
from redis.asyncio import Redis as AsyncRedis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings
from app.services.redis_pool import QUEUE_APPLY, QUEUE_JOBS, RedisSettings, redis_settings_from_url
from app.database import get_async_session
from app.middleware.rate_limit import limiter
from app.models.application import Application
from app.models.base import ApplicationStatus
from app.models.job import Job
from app.schemas.apply import (
    ApplySinglePhase,
    ATSDetectRequest,
    ATSDetectResponse,
    ATSDetectionStatusResponse,
    ApplyBulkRequest,
    ApplyBulkResponse,
    ApplyBulkStatusResponse,
    ApplySingleRequest,
    ApplySingleResponse,
    ApplyStatusResponse,
)

logger = logging.getLogger(__name__)

apply_router = APIRouter(prefix="/api/apply", tags=["apply"])

PROGRESS_PREFIX = "apply_progress:"
BULK_PREFIX = "apply_bulk:"

TERMINAL_STATUSES = frozenset({
    ApplicationStatus.applied,
    ApplicationStatus.applied_with_issues,
    ApplicationStatus.manual_required,
    ApplicationStatus.failed,
})


async def _clear_apply_progress(application_id: uuid.UUID) -> None:
    raw_redis = _get_raw_redis()
    try:
        await raw_redis.delete(f"{PROGRESS_PREFIX}{application_id}")
    finally:
        await raw_redis.aclose()


def _get_redis_settings() -> RedisSettings:
    return redis_settings_from_url(settings.REDIS_URL)


async def _validate_application_ownership(
    session: AsyncSession, application_id: uuid.UUID, user_id: str,
) -> Application:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    if application.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized.",
        )
    return application


def _get_raw_redis() -> AsyncRedis:
    return AsyncRedis.from_url(settings.REDIS_URL, decode_responses=True)


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

    apply_url_passed = (request.apply_url or job.apply_url or "").strip()
    if not apply_url_passed and not (job.source_url or "").strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job has no apply URL or source URL to resolve from.",
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
            apply_url_passed,
            _job_id=f"ats_detect_{application.id}",
            _queue_name=QUEUE_JOBS,
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
            "apply_url": apply_url_passed or None,
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
        notes=application.notes,
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


@apply_router.post("/single", response_model=ApplySingleResponse)
@limiter.limit("5/minute")
async def apply_single(
    request: Request,
    body: ApplySingleRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplySingleResponse:
    application = await _validate_application_ownership(session, body.application_id, user.id)

    if application.status in (
        ApplicationStatus.applied,
        ApplicationStatus.applied_with_issues,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Application already has a submission outcome; auto-apply cannot run again.",
        )

    if application.status == ApplicationStatus.saved:
        job_result = await session.execute(select(Job).where(Job.id == application.job_id))
        job = job_result.scalar_one_or_none()
        apply_url_job = ((job.apply_url or "").strip()) if job else ""
        has_source_url = bool(job and (job.source_url or "").strip())
        if not apply_url_job and not has_source_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Job has no apply URL or listing URL for resolution.",
            )

        application.status = ApplicationStatus.generating
        session.add(application)
        await session.commit()

        await _clear_apply_progress(application.id)

        arq_job_id = ""
        try:
            redis = await arq_create_pool(_get_redis_settings())
            arq_job = await redis.enqueue_job(
                "ats_detect_job",
                str(application.id),
                str(user.id),
                apply_url_job,
                _job_id=f"ats_detect_{application.id}",
                _queue_name=QUEUE_JOBS,
            )
            arq_job_id = arq_job.job_id if arq_job else ""
            await redis.close()
        except Exception as exc:
            logger.error(f"Failed to enqueue auto ATS detection: {exc}")
            application.status = ApplicationStatus.saved
            session.add(application)
            await session.commit()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to start ATS detection.",
            )

        logger.info(
            "apply_single_ats_detect_enqueued",
            extra={
                "application_id": str(application.id),
                "user_id": str(user.id),
            },
        )

        return ApplySingleResponse(
            application_id=application.id,
            task_id=arq_job_id,
            message="ATS detection started; poll status until ready.",
            phase=ApplySinglePhase.detecting,
        )

    if application.status == ApplicationStatus.generating:
        return ApplySingleResponse(
            application_id=application.id,
            task_id="",
            message="ATS detection in progress.",
            phase=ApplySinglePhase.detecting,
        )

    if application.status == ApplicationStatus.manual_required:
        return ApplySingleResponse(
            application_id=application.id,
            task_id="",
            message=application.notes or "Manual completion is required before auto-apply can run.",
            phase=ApplySinglePhase.manual_required,
        )

    if application.status == ApplicationStatus.failed:
        error_msg = application.ats_detection_error or "Application is in failed status."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_msg,
        )

    if application.status == ApplicationStatus.applying:
        return ApplySingleResponse(
            application_id=application.id,
            task_id="",
            message="Auto-apply already running.",
            phase=ApplySinglePhase.applying,
        )

    if application.status != ApplicationStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Application is in '{application.status.value}' status; cannot start auto-apply.",
        )

    application.status = ApplicationStatus.applying
    session.add(application)
    await session.commit()

    await _clear_apply_progress(application.id)

    try:
        redis = await arq_create_pool(_get_redis_settings())
        arq_job = await redis.enqueue_job(
            "apply_single_job",
            str(application.id),
            str(user.id),
            _job_id=f"apply_single_{application.id}",
            _queue_name=QUEUE_APPLY,
        )
        await redis.close()
    except Exception as exc:
        logger.error(f"Failed to enqueue apply single: {exc}")
        application.status = ApplicationStatus.ready
        session.add(application)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start application.",
        )

    logger.info(
        "apply_single_enqueued",
        extra={
            "application_id": str(application.id),
            "user_id": str(user.id),
        },
    )

    return ApplySingleResponse(
        application_id=application.id,
        task_id=arq_job.job_id if arq_job else "",
        message="Application started",
        phase=ApplySinglePhase.applying,
    )


@apply_router.post("/bulk", response_model=ApplyBulkResponse)
@limiter.limit("5/minute")
async def apply_bulk(
    request: Request,
    body: ApplyBulkRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplyBulkResponse:
    if len(body.application_ids) > settings.ATS_APPLY_MAX_BULK:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Maximum {settings.ATS_APPLY_MAX_BULK} applications per bulk request.",
        )

    applications: list[Application] = []
    for app_id in body.application_ids:
        result = await session.execute(
            select(Application).where(Application.id == app_id)
        )
        application = result.scalar_one_or_none()
        if application is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application {app_id} not found.",
            )
        if application.user_id != user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized.",
            )
        if application.status != ApplicationStatus.ready:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application {app_id} is in '{application.status.value}' status, expected 'ready'.",
            )
        applications.append(application)

    for application in applications:
        application.status = ApplicationStatus.applying
        session.add(application)
    await session.commit()

    bulk_task_id = f"apply_bulk_{uuid.uuid4()}"

    try:
        redis = await arq_create_pool(_get_redis_settings())
        await redis.enqueue_job(
            "apply_bulk_job",
            [str(a.id) for a in applications],
            str(user.id),
            bulk_task_id,
            _job_id=bulk_task_id,
            _queue_name=QUEUE_APPLY,
        )
        await redis.close()
    except Exception as exc:
        logger.error(f"Failed to enqueue bulk apply: {exc}")
        for application in applications:
            application.status = ApplicationStatus.ready
            session.add(application)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start bulk application.",
        )

    raw_redis = _get_raw_redis()
    bulk_data = json.dumps({
        "total": len(applications),
        "completed": 0,
        "failed": 0,
        "manual_required": 0,
        "pending": len(applications),
        "results": [],
    })
    await raw_redis.set(f"{BULK_PREFIX}{bulk_task_id}", bulk_data, ex=86400)
    await raw_redis.aclose()

    logger.info(
        "apply_bulk_enqueued",
        extra={
            "bulk_task_id": bulk_task_id,
            "application_ids": [str(a.id) for a in applications],
            "user_id": str(user.id),
        },
    )

    return ApplyBulkResponse(
        bulk_task_id=bulk_task_id,
        application_ids=[a.id for a in applications],
        message=f"Bulk application started for {len(applications)} jobs",
    )


@apply_router.get("/{application_id}/status", response_model=ApplyStatusResponse)
async def apply_status(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplyStatusResponse:
    application = await _validate_application_ownership(session, application_id, user.id)

    step: str | None = None
    steps_completed_list: list[str] | None = None
    resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    error: str | None = application.ats_detection_error

    raw_redis = _get_raw_redis()
    progress_raw = await raw_redis.get(f"{PROGRESS_PREFIX}{application_id}")
    await raw_redis.aclose()

    if progress_raw:
        try:
            progress_data = json.loads(progress_raw)
            working = progress_data.get("working_step")
            current = progress_data.get("current_step")
            step = working if isinstance(working, str) and working.strip() else current
            raw_steps = progress_data.get("steps_completed")
            if isinstance(raw_steps, list):
                steps_completed_list = [str(s) for s in raw_steps if isinstance(s, str)]
            resume_id_str = progress_data.get("resume_id")
            cover_letter_id_str = progress_data.get("cover_letter_id")
            resume_id = uuid.UUID(resume_id_str) if resume_id_str else None
            cover_letter_id = uuid.UUID(cover_letter_id_str) if cover_letter_id_str else None
        except (json.JSONDecodeError, TypeError, ValueError):
            pass

    return ApplyStatusResponse(
        application_id=application.id,
        status=application.status.value if isinstance(application.status, ApplicationStatus) else str(application.status),
        step=step,
        steps_completed=steps_completed_list,
        error=error,
        notes=application.notes,
        resume_id=resume_id,
        cover_letter_id=cover_letter_id,
        screenshot_path=application.ats_screenshot_path,
        manual_url=application.ats_form_url,
    )


@apply_router.get("/{application_id}/stream")
async def apply_stream(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> StreamingResponse:
    await _validate_application_ownership(session, application_id, user.id)

    async def event_generator():
        raw_redis = _get_raw_redis()
        last_progress_sig: tuple[str | None, tuple[str, ...], str | None] | None = None

        try:
            while True:
                progress_raw = await raw_redis.get(f"{PROGRESS_PREFIX}{application_id}")

                working_step: str | None = None
                steps_completed_list: list[str] = []
                current_status = None
                current_error = None
                current_notes = None
                app = None

                if progress_raw:
                    try:
                        progress_data = json.loads(progress_raw)
                        ws = progress_data.get("working_step")
                        working_step = ws if isinstance(ws, str) and ws.strip() else None
                        raw_steps = progress_data.get("steps_completed")
                        if isinstance(raw_steps, list):
                            steps_completed_list = [str(s) for s in raw_steps if isinstance(s, str)]
                    except (json.JSONDecodeError, TypeError):
                        pass

                async with await get_async_session() as check_session:
                    result = await check_session.execute(
                        select(Application).where(Application.id == application_id)
                    )
                    app = result.scalar_one_or_none()
                    if app:
                        current_status = app.status.value if isinstance(app.status, ApplicationStatus) else str(app.status)
                        current_error = app.ats_detection_error
                        current_notes = app.notes

                progress_sig = (working_step, tuple(steps_completed_list), current_status)
                if progress_sig != last_progress_sig:
                    effective_step = working_step
                    event_data = json.dumps({
                        "event": "progress",
                        "application_id": str(application_id),
                        "step": effective_step,
                        "steps_completed": steps_completed_list,
                        "status": current_status,
                        "error": current_error,
                        "notes": current_notes,
                        "manual_url": app.ats_form_url if app else None,
                    })
                    yield f"data: {event_data}\n\n"
                    last_progress_sig = progress_sig

                if current_status and current_status in {s.value for s in TERMINAL_STATUSES}:
                    done_data = json.dumps({
                        "event": "done",
                        "application_id": str(application_id),
                        "status": current_status,
                        "steps_completed": steps_completed_list,
                        "error": current_error,
                        "notes": app.notes if app else None,
                        "manual_url": app.ats_form_url if app else None,
                    })
                    yield f"data: {done_data}\n\n"
                    break

                await asyncio.sleep(1)
        finally:
            await raw_redis.aclose()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@apply_router.get("/bulk/{task_id}/status", response_model=ApplyBulkStatusResponse)
async def apply_bulk_status(
    task_id: str,
    user: CurrentUser = Depends(get_current_user),
) -> ApplyBulkStatusResponse:
    raw_redis = _get_raw_redis()
    bulk_raw = await raw_redis.get(f"{BULK_PREFIX}{task_id}")
    await raw_redis.aclose()

    if bulk_raw is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bulk task not found.",
        )

    try:
        data = json.loads(bulk_raw)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invalid bulk task data.",
        )

    results: list[ApplyStatusResponse] = []
    for r in data.get("results", []):
        app_id = r.get("application_id")
        results.append(ApplyStatusResponse(
            application_id=uuid.UUID(app_id) if app_id else uuid.uuid4(),
            status=r.get("status", "unknown"),
            error=r.get("error"),
        ))

    return ApplyBulkStatusResponse(
        bulk_task_id=task_id,
        total=data.get("total", 0),
        completed=data.get("completed", 0),
        failed=data.get("failed", 0),
        manual_required=data.get("manual_required", 0),
        pending=data.get("pending", 0),
        results=results,
    )
