import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from redis.asyncio import Redis
from sqlalchemy import select, update

from app.config import settings


def _redis_settings_from_url(url: str) -> RedisSettings:
    """Parse redis://host:port/db into RedisSettings."""
    stripped = url.replace("redis://", "")
    parts = stripped.split("/")
    db = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    host_port = parts[0].split(":")
    host = host_port[0] if host_port[0] else "localhost"
    port = int(host_port[1]) if len(host_port) > 1 else 6379
    return RedisSettings(host=host, port=port, database=db)
from app.models.base import ApplicationStatus

logger = logging.getLogger(__name__)

LOCK_PREFIX = "apply_lock:"
PROGRESS_PREFIX = "apply_progress:"
BULK_PREFIX = "apply_bulk:"


async def apply_single_job(
    ctx: dict[str, Any],
    application_id: str,
    user_id: str,
    bulk_task_id: str | None = None,
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.models.application import Application
    from app.services.ai_client import AIClient
    from app.services.ai_pipeline import AIPipeline
    from app.services.apply_orchestrator import AutoApplyOrchestrator
    from app.services.browser_service import BrowserService

    redis: Redis = ctx["redis"]

    lock_key = f"{LOCK_PREFIX}{application_id}"
    locked = await redis.get(lock_key)
    if locked:
        logger.info(
            "apply_single_skipped_locked",
            extra={"application_id": application_id, "bulk_task_id": bulk_task_id},
        )
        return {"status": "skipped", "reason": "lock_held"}

    async def session_factory():
        return async_session_factory()

    try:
        async with BrowserService(
            headless=settings.ATS_DETECT_HEADLESS,
            timeout_ms=settings.ATS_FILL_TIMEOUT_SECONDS * 1000,
            screenshot_dir=settings.ATS_SCREENSHOT_DIR,
        ) as browser:
            pipeline = AIPipeline(ai_client=AIClient())
            orchestrator = AutoApplyOrchestrator(
                browser_service=browser,
                ai_pipeline=pipeline,
                session_factory=session_factory,
                redis=redis,
            )
            result = await orchestrator.run(
                application_id=uuid.UUID(application_id),
                user_id=uuid.UUID(user_id),
            )

    except Exception as exc:
        logger.error(
            f"apply_single_job failed for {application_id}: {exc}",
            exc_info=True,
        )

        try:
            async with async_session_factory() as session:
                stmt = (
                    update(Application)
                    .where(Application.id == uuid.UUID(application_id))
                    .values(
                        status=ApplicationStatus.failed,
                        ats_detection_error=str(exc),
                    )
                )
                await session.execute(stmt)
                await session.commit()
        except Exception:
            pass

        result_dict = {
            "status": "failed",
            "error": str(exc),
            "application_id": application_id,
        }

        if bulk_task_id:
            await _update_bulk_progress(redis, bulk_task_id, result_dict)

        return result_dict

    result_dict = result.model_dump()

    if bulk_task_id:
        await _update_bulk_progress(redis, bulk_task_id, result_dict)

    return result_dict


async def apply_bulk_job(
    ctx: dict[str, Any],
    application_ids: list[str],
    user_id: str,
    bulk_task_id: str,
) -> dict[str, Any]:
    redis: Redis = ctx["redis"]

    bulk_key = f"{BULK_PREFIX}{bulk_task_id}"
    total = len(application_ids)

    initial_data = json.dumps({
        "total": total,
        "completed": 0,
        "failed": 0,
        "manual_required": 0,
        "pending": total,
        "results": [],
    })
    await redis.set(bulk_key, initial_data, ex=86400)

    for app_id in application_ids:
        try:
            await apply_single_job(ctx, app_id, user_id, bulk_task_id=bulk_task_id)
        except Exception as exc:
            logger.error(
                f"bulk_apply_individual_failed: {app_id}: {exc}",
                exc_info=True,
            )
            await _update_bulk_progress(redis, bulk_task_id, {
                "status": "failed",
                "error": str(exc),
                "application_id": app_id,
            })

    return {"bulk_task_id": bulk_task_id, "total": total}


async def sweep_stale_apply_jobs(ctx: dict[str, Any]) -> None:
    from app.database import async_session_factory
    from app.models.application import Application

    redis: Redis = ctx["redis"]
    threshold_minutes = settings.ATS_APPLY_STALE_MINUTES
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    cutoff_naive = cutoff.replace(tzinfo=None)

    async with async_session_factory() as session:
        stmt = (
            update(Application)
            .where(
                Application.status == ApplicationStatus.applying,
                Application.updated_at < cutoff_naive,
            )
            .values(
                status=ApplicationStatus.failed,
                ats_detection_error="Apply job timed out (stale sweeper)",
            )
            .returning(Application.id)
        )
        result = await session.execute(stmt)
        reverted_ids = result.scalars().all()
        await session.commit()

        for app_id in reverted_ids:
            lock_key = f"{LOCK_PREFIX}{app_id}"
            await redis.delete(lock_key)
            progress_key = f"{PROGRESS_PREFIX}{app_id}"
            await redis.delete(progress_key)

        if reverted_ids:
            logger.info(
                "stale_apply_sweep",
                extra={
                    "reverted_count": len(reverted_ids),
                    "reverted_ids": [str(i) for i in reverted_ids],
                },
            )


async def _update_bulk_progress(redis: Redis, bulk_task_id: str, result: dict[str, Any]) -> None:
    bulk_key = f"{BULK_PREFIX}{bulk_task_id}"
    raw = await redis.get(bulk_key)
    if raw is None:
        return

    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return

    data["pending"] = max(0, data.get("pending", 0) - 1)
    result_status = result.get("status", "failed")

    if result_status == "applied":
        data["completed"] = data.get("completed", 0) + 1
    elif result_status in ("manual_required", "applied_with_issues"):
        data["manual_required"] = data.get("manual_required", 0) + 1
    else:
        data["failed"] = data.get("failed", 0) + 1

    results = data.get("results", [])
    results.append(result)
    data["results"] = results

    await redis.set(bulk_key, json.dumps(data), ex=86400)


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Apply worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Apply worker shutting down")


class ApplyWorkerSettings:
    functions = [apply_single_job, apply_bulk_job]
    cron_jobs = [
        cron(
            sweep_stale_apply_jobs,
            second=0,
            max_tries=1,
        ),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings_from_url(settings.REDIS_URL)
