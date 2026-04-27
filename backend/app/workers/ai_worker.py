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


async def generate_cover_letter_job(
    ctx: dict[str, Any],
    cover_letter_id: str,
    user_id: str,
    candidate_profile_id: str,
    job_description: str,
    tone: str = "professional",
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.models.cover_letter import CoverLetter
    from app.services.ai_client import AIClient
    from app.services.ai_pipeline import AIPipeline
    from sqlalchemy import select

    pipeline = AIPipeline(
        ai_client=AIClient(),
    )

    async def session_factory():
        return async_session_factory()

    async with async_session_factory() as session:
        result = await session.execute(select(CoverLetter).where(CoverLetter.id == cover_letter_id))
        cover_letter = result.scalar_one_or_none()
        if cover_letter is None:
            logger.error(f"CoverLetter {cover_letter_id} not found in DB")
            return {"status": "error", "error": "CoverLetter not found"}
        cover_letter.status = "generating"
        await session.commit()

    try:
        pipeline_result = await pipeline.run_cover_letter_pipeline(
            job_description=job_description,
            candidate_profile_id=candidate_profile_id,
            user_id=user_id,
            tone=tone,
            get_session=session_factory,
        )

        cover_letter_data = pipeline_result.get("cover_letter", {})
        async with async_session_factory() as session:
            result = await session.execute(select(CoverLetter).where(CoverLetter.id == cover_letter_id))
            cover_letter = result.scalar_one_or_none()
            if cover_letter:
                cover_letter.status = "completed"
                cover_letter.content_json = cover_letter_data
                cover_letter.content = cover_letter_data.get("full_text", "")
                cover_letter.tone = cover_letter_data.get("tone_used", tone)
                cover_letter.ai_model_used = "glm-4-plus"
                await session.commit()

        logger.info(
            "Cover letter generation complete",
            extra={"cover_letter_id": cover_letter_id, "user_id": user_id, "tone": tone},
        )
        return pipeline_result
    except Exception as exc:
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(CoverLetter).where(CoverLetter.id == cover_letter_id))
                cover_letter = result.scalar_one_or_none()
                if cover_letter:
                    cover_letter.status = "failed"
                    await session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to mark cover letter as failed: {db_exc}")

        logger.error(
            f"Cover letter generation failed: {exc}",
            extra={"cover_letter_id": cover_letter_id, "user_id": user_id},
        )
        raise


async def generate_interview_prep_job(
    ctx: dict[str, Any],
    prep_id: str,
    user_id: str,
    candidate_profile_id: str,
    job_description: str,
) -> dict[str, Any]:
    from app.database import async_session_factory
    from app.models.interview import InterviewPrep
    from app.services.ai_client import AIClient
    from app.services.ai_pipeline import AIPipeline
    from sqlalchemy import select

    pipeline = AIPipeline(
        ai_client=AIClient(),
    )

    async def session_factory():
        return async_session_factory()

    async with async_session_factory() as session:
        result = await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
        prep = result.scalar_one_or_none()
        if prep is None:
            logger.error(f"InterviewPrep {prep_id} not found in DB")
            return {"status": "error", "error": "InterviewPrep not found"}
        prep.status = "generating"
        await session.commit()

    try:
        pipeline_result = await pipeline.run_interview_prep_pipeline(
            job_description=job_description,
            candidate_profile_id=candidate_profile_id,
            user_id=user_id,
            get_session=session_factory,
        )

        questions_data = pipeline_result.get("questions", [])
        async with async_session_factory() as session:
            result = await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
            prep = result.scalar_one_or_none()
            if prep:
                prep.status = "completed"
                prep.questions = questions_data
                await session.commit()

        logger.info(
            "Interview prep generation complete",
            extra={"prep_id": prep_id, "user_id": user_id, "question_count": len(questions_data)},
        )
        return pipeline_result
    except Exception as exc:
        try:
            async with async_session_factory() as session:
                result = await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
                prep = result.scalar_one_or_none()
                if prep:
                    prep.status = "failed"
                    await session.commit()
        except Exception as db_exc:
            logger.error(f"Failed to mark interview prep as failed: {db_exc}")

        logger.error(
            f"Interview prep generation failed: {exc}",
            extra={"prep_id": prep_id, "user_id": user_id},
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
    functions = [generate_resume_job, generate_cover_letter_job, generate_interview_prep_job]
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
