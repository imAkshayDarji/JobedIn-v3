import logging
import uuid
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.config import settings

logger = logging.getLogger(__name__)


async def generate_resume_job(ctx: dict[str, Any], resume_id: str, user_id: str, candidate_profile_id: str, job_description: str) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.models.resume import Resume
    from app.services.ai_client import AIClient
    from app.services.ai_pipeline import AIPipeline
    from sqlalchemy import select

    pipeline = AIPipeline(
        ai_client=AIClient(),
    )

    async def session_factory():
        return async_session_factory()

    # Update resume status to "generating"
    async with async_session_factory() as session:
        result = await session.execute(select(Resume).where(Resume.id == resume_id))
        resume = result.scalar_one_or_none()
        if resume is None:
            logger.error(f"Resume {resume_id} not found in DB")
            return {"status": "error", "error": "Resume not found"}
        resume.status = "generating"
        await session.commit()

    try:
        pipeline_result = await pipeline.run_full_pipeline(
            job_description=job_description,
            candidate_profile_id=candidate_profile_id,
            user_id=user_id,
            get_session=session_factory,
        )

        # Persist result to resume record
        async with async_session_factory() as session:
            result = await session.execute(select(Resume).where(Resume.id == resume_id))
            resume = result.scalar_one_or_none()
            if resume:
                resume.status = "completed"
                resume.content_json = pipeline_result.get("resume")
                resume.ats_score = pipeline_result.get("ats_result", {}).get("overall_score")
                resume.ats_breakdown = pipeline_result.get("ats_result")
                await session.commit()

        logger.info(
            "Resume generation complete",
            extra={"resume_id": resume_id, "user_id": user_id, "ats_score": pipeline_result.get("ats_result", {}).get("overall_score")},
        )
        return pipeline_result
    except Exception as exc:
        # Mark resume as failed
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(Resume).where(Resume.id == resume_id))
                resume = result.scalar_one_or_none()
                if resume:
                    resume.status = "failed"
                    await session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to mark resume as failed: {db_exc}")

        logger.error(
            f"Resume generation failed: {exc}",
            extra={"resume_id": resume_id, "user_id": user_id},
        )
        raise


async def sweep_stale_jobs(ctx: dict[str, Any]) -> None:
    from datetime import datetime, timedelta, timezone

    from redis.asyncio import Redis

    redis: Redis = ctx["redis"]
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    cutoff_str = cutoff.isoformat()

    cursor = b"0"
    while True:
        cursor, keys = await redis.hscan("arq:job:result", cursor)
        for key_fragment in keys:
            pass

        if cursor == b"0":
            break

    logger.info("Stale job sweep complete")


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("AI worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("AI worker shutting down")


class WorkerSettings:
    functions = [generate_resume_job]
    cron_jobs = [
        cron(
            sweep_stale_jobs,
            second=0,
            max_tries=1,
        ),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings(
        host=settings.REDIS_URL.split("@")[-1].split(":")[0] if "@" in settings.REDIS_URL else "localhost",
        port=int(settings.REDIS_URL.split(":")[-1].split("/")[0]) if ":" in settings.REDIS_URL else 6379,
        database=int(settings.REDIS_URL.rstrip("/").split("/")[-1]) if "/" in settings.REDIS_URL else 0,
    )
