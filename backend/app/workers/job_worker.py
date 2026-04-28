import logging
import time
import uuid
from typing import Any

from arq.connections import RedisSettings

from app.config import settings
from app.services.job_discovery import IngestResult

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
                    await redis.enqueue_job("match_jobs_job", user_id)
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

    start = time.monotonic()

    async with async_session_factory() as session:
        service = JobDiscoveryService(session)

        try:
            result = await service.run_api_discovery(
                keywords=keywords,
                location=location,
                sources=sources,
            )
        except Exception as exc:
            logger.error(f"API discovery failed: {exc}", exc_info=True)
            result = IngestResult(errors=[str(exc)])

        duration = time.monotonic() - start

        log_entry = DiscoveryLog(
            sources=sources or [],
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

        return result.model_dump()


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
                user_id=uuid.UUID(user_id),
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


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Job worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Job worker shutting down")


class JobWorkerSettings:
    functions = [linkedin_discovery_job, api_discovery_job, match_jobs_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=settings.REDIS_URL.split("@")[-1].split(":")[0] if "@" in settings.REDIS_URL else "localhost",
        port=int(settings.REDIS_URL.split(":")[-1].split("/")[0]) if ":" in settings.REDIS_URL else 6379,
        database=int(settings.REDIS_URL.rstrip("/").split("/")[-1]) if "/" in settings.REDIS_URL else 0,
    )
