import asyncio
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from arq import cron
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.job_discovery import IngestResult
from app.services.redis_pool import QUEUE_JOBS, redis_settings_from_url


logger = logging.getLogger(__name__)


async def linkedin_discovery_job(
    ctx: dict[str, Any],
    user_id: str,
    keywords: list[str],
    location: str | None = None,
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.services.job_discovery import JobDiscoveryService
    from app.services.job_sources.exceptions import (
        LinkedInAuthError,
        LinkedInCAPTCHAError,
        LinkedInTimeoutError,
    )

    async with async_session_factory() as session:
        service = JobDiscoveryService(session)

        try:
            result = await service.run_linkedin_discovery(
                user_id=uuid.UUID(user_id),
                keywords=keywords,
                location=location,
            )

            if result.new_count > 0:
                try:
                    redis = await ctx["redis"]
                    await redis.enqueue_job(
                        "match_jobs_job",
                        user_id,
                        _queue_name=QUEUE_JOBS,
                    )
                except Exception:
                    logger.warning(f"Failed to enqueue match job for user {user_id}")

            return result.model_dump()

        except LinkedInCAPTCHAError as exc:
            logger.warning(f"LinkedIn CAPTCHA for user {user_id}: {exc}")
            error_result = IngestResult(errors=[f"CAPTCHA detected: {exc}"])
            return error_result.model_dump()

        except LinkedInTimeoutError as exc:
            logger.warning(f"LinkedIn timeout for user {user_id}: {exc}")
            error_result = IngestResult(errors=[f"Timeout: {exc}"])
            return error_result.model_dump()

        except LinkedInAuthError as exc:
            logger.warning(f"LinkedIn auth failed for user {user_id}: {exc}")
            error_result = IngestResult(errors=[f"Auth failed: {exc}"])
            return error_result.model_dump()

        except Exception as exc:
            logger.error(f"LinkedIn discovery failed for user {user_id}: {exc}", exc_info=True)
            raise


async def api_discovery_job(
    ctx: dict[str, Any],
    keywords: list[str],
    location: str | None = None,
    sources: list[str] | None = None,
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.models.discovery_log import DiscoveryLog
    from app.services.job_discovery import JobDiscoveryService
    from app.services.job_sources import active_api_sources

    start = time.monotonic()

    resolved_sources = sources if sources is not None else active_api_sources()

    async with async_session_factory() as session:
        service = JobDiscoveryService(session)

        try:
            result = await service.run_api_discovery(
                keywords=keywords,
                location=location,
                sources=resolved_sources,
            )
        except Exception as exc:
            logger.error(f"API discovery failed: {exc}", exc_info=True)
            result = IngestResult(errors=[str(exc)])

        duration = time.monotonic() - start

        log_entry = DiscoveryLog(
            sources=resolved_sources,
            keywords=keywords,
            location=location,
            total_found=result.total_found,
            new_count=result.new_count,
            updated_count=result.updated_count,
            skipped_count=result.skipped_count,
            errors=result.errors or None,
            duration_seconds=round(duration, 2),
        )
        session.add(log_entry)
        await session.commit()

        # Schedule background detail fetches for jobs with short descriptions
        if result.new_count > 0:
            try:
                redis = await ctx["redis"]
                await _schedule_detail_fetches(redis, session)
            except Exception as exc:
                logger.warning(f"Failed to schedule detail fetches: {exc}")

        return result.model_dump()


async def _schedule_detail_fetches(redis: object, session: AsyncSession) -> None:
    """Find recently ingested jobs with short descriptions and enqueue detail fetches."""
    from app.models.base import JobSource
    from app.models.job import Job
    from app.services.job_sources import active_api_sources
    from sqlalchemy import select

    from datetime import datetime, timedelta, timezone

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
    cutoff_naive = cutoff.replace(tzinfo=None)

    detail_sources = {"jsearch", "adzuna", "reed"} & set(active_api_sources())

    for source_name in detail_sources:
        stmt = (
            select(Job.id, Job.external_id)
            .where(
                Job.source == JobSource(source_name),
                Job.created_at >= cutoff_naive,
            )
        )
        rows = (await session.execute(stmt)).all()

        for job_id, external_id in rows:
            job_stmt = select(Job.description).where(Job.id == job_id)
            desc_result = await session.execute(job_stmt)
            desc = desc_result.scalar_one_or_none() or ""
            if len(desc.strip()) < 200:
                await redis.enqueue_job(
                    "fetch_job_detail_job",
                    source_name,
                    str(external_id),
                    _queue_name=QUEUE_JOBS,
                )


async def match_jobs_job(
    ctx: dict[str, Any],
    user_id: str,
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.services.match_scorer import MatchScorer

    async with async_session_factory() as session:
        scorer = MatchScorer(session)

        try:
            results = await scorer.score_jobs_batch(
                user_id=user_id,
            )
            return {
                "user_id": user_id,
                "scored_count": len(results),
                "avg_score": round(
                    sum(r.match_score for r in results) / len(results), 2
                ) if results else 0.0,
            }
        except Exception as exc:
            logger.error(f"Match scoring failed for user {user_id}: {exc}", exc_info=True)
            raise


async def ats_detect_job(
    ctx: dict[str, Any],
    application_id: str,
    user_id: str,
    apply_url: str,
) -> dict[str, Any]:
    """ARQ worker: detect ATS platform for a job application.

    Guards:
    - Catch-all rescue: reverts status to 'saved' on any error
    - Deleted-row guard: graceful exit if Application is gone
    """
    from app.database import async_session_factory
    from app.models.application import Application
    from app.models.base import ApplicationStatus
    from app.models.job import Job
    from app.services.ats_detector import ATSDetector
    from app.services.browser_service import BrowserService

    async with async_session_factory() as session:
        result_stmt = await session.execute(
            select(Application).where(Application.id == uuid.UUID(application_id))
        )
        application = result_stmt.scalar_one_or_none()

        if application is None:
            logger.info(
                "ats_detect_skipped_deleted",
                extra={"application_id": application_id},
            )
            return {"status": "skipped", "reason": "application_deleted"}

        if str(application.user_id) != user_id:
            logger.warning(
                "ats_detect_user_mismatch",
                extra={"application_id": application_id, "expected_user": str(application.user_id)},
            )
            return {"status": "skipped", "reason": "user_mismatch"}

        try:
            job_result = await session.execute(select(Job).where(Job.id == application.job_id))
            job = job_result.scalar_one_or_none()
            if job is None:
                application.ats_detection_error = "Job row missing"
                application.status = ApplicationStatus.saved
                session.add(application)
                await session.commit()
                return {"status": "failed", "error": "job_not_found"}

            apply_candidate = (apply_url or "").strip()

            async with BrowserService(
                headless=settings.ATS_DETECT_HEADLESS,
                timeout_ms=settings.ATS_DETECT_TIMEOUT_MS,
                screenshot_dir=settings.ATS_SCREENSHOT_DIR,
            ) as browser:
                if not apply_candidate:
                    from app.services.url_resolver import URLResolver

                    resolver = URLResolver(browser)
                    resolved = await resolver.resolve(job)
                    apply_candidate = (resolved.apply_url or "").strip()
                    if not apply_candidate:
                        application.status = ApplicationStatus.manual_required
                        application.ats_platform = None
                        application.ats_detection_method = "failed"
                        application.ats_confidence = 0.0
                        application.ats_form_url = job.source_url or job.apply_url
                        application.notes = resolved.error or "Could not resolve an apply URL automatically."
                        application.ats_detection_error = None
                        application.ats_difficulty = None
                        session.add(application)
                        await session.commit()
                        logger.info(
                            "ats_detect_url_unresolved",
                            extra={"application_id": application_id},
                        )
                        return {"status": "manual_required", "reason": "url_resolution_failed"}

                detector = ATSDetector(browser)
                result = await detector.detect(apply_candidate)

            application.ats_platform = result.ats_platform
            application.ats_detection_method = result.detection_method
            application.ats_confidence = result.confidence
            application.ats_form_url = result.form_url or apply_candidate
            application.ats_detected_fields = result.detected_fields
            application.ats_screenshot_path = result.screenshot_path
            application.ats_detection_error = result.error
            application.ats_difficulty = result.difficulty.value if result.difficulty else None
            application.status = ApplicationStatus.ready

            session.add(application)
            await session.commit()

            logger.info(
                "ats_detect_complete",
                extra={
                    "application_id": application_id,
                    "user_id": user_id,
                    "ats_platform": result.ats_platform,
                    "detection_method": result.detection_method,
                    "confidence": result.confidence,
                    "detection_time_ms": result.detection_time_ms,
                    "difficulty": result.difficulty.value,
                },
            )

            return {
                "status": "completed",
                "ats_platform": result.ats_platform,
                "difficulty": result.difficulty.value,
                "detection_time_ms": result.detection_time_ms,
            }

        except Exception as exc:
            logger.error(
                f"ATS detection failed for application {application_id}: {exc}",
                exc_info=True,
            )

            try:
                application.ats_detection_error = str(exc)
                application.status = ApplicationStatus.saved
                session.add(application)
                await session.commit()
            except Exception:
                pass

            return {"status": "failed", "error": str(exc)}


async def sweep_stale_ats_detections(ctx: dict[str, Any]) -> None:
    """ARQ cron: revert Applications stuck in 'generating' for > threshold minutes."""
    from sqlalchemy import select, update

    from app.database import async_session_factory
    from app.models.application import Application
    from app.models.base import ApplicationStatus

    threshold_minutes = settings.ATS_STALE_DETECTION_MINUTES
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    cutoff_naive = cutoff.replace(tzinfo=None)

    async with async_session_factory() as session:
        stmt = (
            update(Application)
            .where(
                Application.status == ApplicationStatus.generating,
                Application.updated_at < cutoff_naive,
            )
            .values(
                status=ApplicationStatus.saved,
                ats_detection_error="Detection timed out (stale sweeper)",
            )
            .returning(Application.id)
        )
        result = await session.execute(stmt)
        reverted_ids = result.scalars().all()
        await session.commit()

        if reverted_ids:
            logger.info(
                "stale_ats_sweep",
                extra={
                    "reverted_count": len(reverted_ids),
                    "reverted_ids": [str(i) for i in reverted_ids],
                },
            )


async def fetch_job_detail_job(
    ctx: dict[str, Any],
    source_name: str,
    external_id: str,
) -> dict[str, Any]:
    """ARQ worker: fetch full details for a single job and update the database."""
    from app.database import async_session_factory
    from app.models.base import JobSource
    from app.services.job_discovery import JobDiscoveryService
    from app.services.job_sources import ADAPTER_REGISTRY

    adapter_cls = ADAPTER_REGISTRY.get(source_name)
    if not adapter_cls:
        return {"status": "skipped", "reason": f"Unknown source: {source_name}"}

    async with async_session_factory() as session:
        from app.models.job import Job
        from sqlalchemy import select

        result_stmt = await session.execute(
            select(Job).where(
                Job.source == JobSource(source_name),
                Job.external_id == external_id,
            )
        )
        job = result_stmt.scalar_one_or_none()
        if job is None:
            return {"status": "skipped", "reason": "job_not_found"}

        if job.description and len(job.description.strip()) >= 200:
            return {"status": "skipped", "reason": "already_has_description"}

        try:
            import httpx

            adapter = adapter_cls()
            async with httpx.AsyncClient(timeout=httpx.Timeout(15.0)) as client:
                detail = await adapter.fetch_detail(client, external_id)

            if detail and detail.get("description"):
                job.description = detail["description"]
                if detail.get("salary_min") and not job.salary_min:
                    job.salary_min = detail["salary_min"]
                if detail.get("salary_max") and not job.salary_max:
                    job.salary_max = detail["salary_max"]
                session.add(job)
                await session.commit()
                return {"status": "completed", "description_length": len(job.description)}

            return {"status": "skipped", "reason": "no_detail_returned"}
        except Exception as exc:
            logger.warning(f"Failed to fetch detail for {source_name}/{external_id}: {exc}")
            return {"status": "failed", "error": str(exc)}


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Job worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Job worker shutting down")


class JobWorkerSettings:
    queue_name = "arq:queue:jobs"
    functions = [linkedin_discovery_job, api_discovery_job, match_jobs_job, ats_detect_job, fetch_job_detail_job]
    cron_jobs = [
        cron(
            sweep_stale_ats_detections,
            second=0,
            max_tries=1,
        ),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = redis_settings_from_url(settings.REDIS_URL)
