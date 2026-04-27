import logging
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


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("Job worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("Job worker shutting down")


class JobWorkerSettings:
    functions = [linkedin_discovery_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=settings.REDIS_URL.split("@")[-1].split(":")[0] if "@" in settings.REDIS_URL else "localhost",
        port=int(settings.REDIS_URL.split(":")[-1].split("/")[0]) if ":" in settings.REDIS_URL else 6379,
        database=int(settings.REDIS_URL.rstrip("/").split("/")[-1]) if "/" in settings.REDIS_URL else 0,
    )
