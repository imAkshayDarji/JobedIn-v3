import logging
import uuid
from typing import Any

from arq import cron
from arq.connections import RedisSettings

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

logger = logging.getLogger(__name__)


async def _persist_token_usage(
    session: Any,
    user_id: str,
    token_usage: dict[str, Any],
) -> None:
    from app.models.ai_usage import AITokenUsage

    for entry in token_usage.get("detail", []):
        record = AITokenUsage(
            user_id=uuid.UUID(user_id) if isinstance(user_id, str) else user_id,
            task=entry["task"],
            model_used=entry["model_used"],
            prompt_tokens=entry["prompt_tokens"],
            completion_tokens=entry["completion_tokens"],
            total_tokens=entry["total_tokens"],
            latency_ms=entry["latency_ms"],
        )
        session.add(record)


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

        token_usage = pipeline_result.get("token_usage", {})

        async with async_session_factory() as session:
            result = await session.execute(select(Resume).where(Resume.id == resume_id))
            resume = result.scalar_one_or_none()
            if resume:
                resume.status = "completed"
                resume.content_json = pipeline_result.get("resume")
                resume.ats_score = pipeline_result.get("ats_result", {}).get("overall_score")
                resume.ats_breakdown = pipeline_result.get("ats_result")

                if token_usage.get("calls", 0) > 0:
                    usage_detail = []
                    for u in pipeline._token_usage:
                        usage_detail.append({
                            "task": u["task"],
                            "model_used": u["model_used"],
                            "prompt_tokens": u["prompt_tokens"],
                            "completion_tokens": u["completion_tokens"],
                            "total_tokens": u["total_tokens"],
                            "latency_ms": u["latency_ms"],
                        })
                    await _persist_token_usage(session, user_id, {"detail": usage_detail})

                await session.commit()

        logger.info(
            "Resume generation complete",
            extra={"resume_id": resume_id, "user_id": user_id, "ats_score": pipeline_result.get("ats_result", {}).get("overall_score")},
        )
        return pipeline_result
    except Exception as exc:
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
        token_usage = pipeline_result.get("token_usage", {})
        models_used = token_usage.get("models_used", [])
        ai_model_used = models_used[-1] if models_used else "unknown"

        async with async_session_factory() as session:
            result = await session.execute(select(CoverLetter).where(CoverLetter.id == cover_letter_id))
            cover_letter = result.scalar_one_or_none()
            if cover_letter:
                cover_letter.status = "completed"
                cover_letter.content_json = cover_letter_data
                cover_letter.content = cover_letter_data.get("full_text", "")
                cover_letter.tone = cover_letter_data.get("tone_used", tone)
                cover_letter.ai_model_used = ai_model_used

                if token_usage.get("calls", 0) > 0:
                    usage_detail = []
                    for u in pipeline._token_usage:
                        usage_detail.append({
                            "task": u["task"],
                            "model_used": u["model_used"],
                            "prompt_tokens": u["prompt_tokens"],
                            "completion_tokens": u["completion_tokens"],
                            "total_tokens": u["total_tokens"],
                            "latency_ms": u["latency_ms"],
                        })
                    await _persist_token_usage(session, user_id, {"detail": usage_detail})

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
        token_usage = pipeline_result.get("token_usage", {})

        async with async_session_factory() as session:
            result = await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
            prep = result.scalar_one_or_none()
            if prep:
                prep.status = "completed"
                prep.questions = questions_data

                if token_usage.get("calls", 0) > 0:
                    usage_detail = []
                    for u in pipeline._token_usage:
                        usage_detail.append({
                            "task": u["task"],
                            "model_used": u["model_used"],
                            "prompt_tokens": u["prompt_tokens"],
                            "completion_tokens": u["completion_tokens"],
                            "total_tokens": u["total_tokens"],
                            "latency_ms": u["latency_ms"],
                        })
                    await _persist_token_usage(session, user_id, {"detail": usage_detail})

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

    from app.database import async_session_factory
    from app.models.interview import InterviewPrep
    from app.models.cover_letter import CoverLetter
    from app.models.resume import Resume
    from sqlalchemy import select

    redis = ctx["redis"]
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)

    stale_count = 0
    cursor = b"0"
    while True:
        cursor, keys = await redis.hscan("arq:job:result", cursor)
        for key in keys:
            job_data = await redis.hget("arq:job:result", key)
            if job_data is None:
                continue

            try:
                import json
                data = json.loads(job_data)
                job_result = data.get("result")
                if job_result is not None:
                    continue

                enqueue_time_str = data.get("enqueue_time")
                if enqueue_time_str is None:
                    continue

                enqueue_time = datetime.fromisoformat(enqueue_time_str)
                if enqueue_time.tzinfo is None:
                    enqueue_time = enqueue_time.replace(tzinfo=timezone.utc)

                if enqueue_time >= cutoff:
                    continue

            except (json.JSONDecodeError, ValueError, TypeError):
                continue

            stale_count += 1
            await redis.hdel("arq:job:result", key)

    async with async_session_factory() as session:
        stale_statuses = ["generating"]

        for model_cls, label in [(Resume, "resume"), (CoverLetter, "cover_letter"), (InterviewPrep, "interview_prep")]:
            stmt = select(model_cls).where(
                model_cls.status.in_(stale_statuses),
                model_cls.updated_at < cutoff,
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
            for record in records:
                record.status = "failed"
                stale_count += 1
                logger.info(f"Marked stale {label} {record.id} as failed")
        await session.commit()

    logger.info(f"Stale job sweep complete, cleaned {stale_count} stale jobs")


async def startup(ctx: dict[str, Any]) -> None:
    logger.info("AI worker starting")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("AI worker shutting down")


class WorkerSettings:
    queue_name = "arq:queue:ai"
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
    redis_settings = _redis_settings_from_url(settings.REDIS_URL)
