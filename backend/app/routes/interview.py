import json
import logging
import uuid
from datetime import datetime, timedelta

from arq import create_pool as arq_create_pool
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi.util import get_remote_address
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.config import settings as app_settings
from app.services.redis_pool import QUEUE_AI, RedisSettings, redis_settings_from_url
from app.database import get_async_session
from app.middleware.rate_limit import limiter
from app.models.candidate import CandidateProfile
from app.models.interview import InterviewPrep, InterviewSession
from app.models.job import Job
from app.schemas.interview import (
    ChatEvaluation,
    ChatQuestion,
    InterviewChatRequest,
    InterviewChatResponse,
    InterviewPrepListItem,
    InterviewPrepListResponse,
    InterviewPrepStatusResponse,
    InterviewSessionDetail,
    InterviewSessionListItem,
    InterviewSessionListResponse,
    InterviewSetupRequest,
    InterviewSetupResponse,
    SessionMessage,
)
from app.services.ai_client import AIClient
from app.services.ai_pipeline import AIPipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["interview"])

DEDUP_WINDOW_MINUTES = 5

CATEGORIES = ["company_research", "technical", "behavioral", "culture_fit"]


def _get_redis_settings() -> RedisSettings:
    return redis_settings_from_url(app_settings.REDIS_URL)


async def _enqueue_interview_prep_job(
    prep_id: str,
    user_id: str,
    profile_id: str,
    job_description: str,
) -> None:
    redis = await arq_create_pool(_get_redis_settings())
    await redis.enqueue_job(
        "generate_interview_prep_job",
        prep_id,
        user_id,
        profile_id,
        job_description,
        _queue_name=QUEUE_AI,
    )
    await redis.close()


async def _resolve_profile(
    user_id: uuid.UUID, session: AsyncSession
) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )
    if not profile.onboarding_completed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Please complete onboarding before using interview coach.",
        )
    return profile


async def _check_ownership(prep: InterviewPrep, user: CurrentUser) -> None:
    if str(prep.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this interview prep.",
        )


async def _check_session_ownership(session_obj: InterviewSession, user: CurrentUser) -> None:
    if str(session_obj.user_id) != str(user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session.",
        )


def _pick_next_question(
    questions: list[dict],
    messages: list[dict],
    current_difficulty: int,
    last_score: float | None = None,
) -> dict | None:
    asked_questions = {
        msg["content"] for msg in messages if msg.get("role") == "question"
    }

    new_difficulty = current_difficulty
    if last_score is not None:
        if last_score >= 7 and current_difficulty < 3:
            new_difficulty = current_difficulty + 1
        elif last_score < 4 and current_difficulty > 1:
            new_difficulty = current_difficulty - 1

    available = [
        q for q in questions
        if q["question"] not in asked_questions
    ]
    if not available:
        return None

    difficulty_match = [q for q in available if q["difficulty"] == new_difficulty]
    if difficulty_match:
        asked_categories = [
            msg.get("category") for msg in messages if msg.get("role") == "question"
        ]
        cat_counts = {c: asked_categories.count(c) for c in CATEGORIES}
        least_used = min(CATEGORIES, key=lambda c: cat_counts.get(c, 0))
        cat_match = [q for q in difficulty_match if q["category"] == least_used]
        if cat_match:
            return {**cat_match[0], "_adjusted_difficulty": new_difficulty}
        return {**difficulty_match[0], "_adjusted_difficulty": new_difficulty}

    return {**available[0], "_adjusted_difficulty": new_difficulty}


@router.post("/setup", response_model=InterviewSetupResponse)
@limiter.limit("5/minute")
async def setup_interview_prep(
    request: Request,
    body: InterviewSetupRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewSetupResponse:
    profile = await _resolve_profile(user.id, session)

    job_description: str | None = None
    job_id: uuid.UUID | None = body.job_id
    job_title: str | None = None
    company_name: str | None = None

    if body.job_id:
        job_result = await session.execute(
            select(Job).where(Job.id == body.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found.",
            )
        job_description = job.description or ""
        job_title = job.title
        company_name = job.company
    else:
        job_description = body.job_description
        job_title = body.job_title
        company_name = body.company_name

    if job_id:
        cutoff = datetime.utcnow() - timedelta(minutes=DEDUP_WINDOW_MINUTES)
        existing_result = await session.execute(
            select(InterviewPrep).where(
                InterviewPrep.user_id == user.id,
                InterviewPrep.job_id == job_id,
                InterviewPrep.created_at > cutoff,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing and existing.status == "completed":
            logger.info(
                "interview_prep_dedup_hit",
                extra={"user_id": str(user.id), "job_id": str(job_id), "prep_id": str(existing.id)},
            )
            return InterviewSetupResponse(prep_id=existing.id, status="completed")

    prep = InterviewPrep(
        user_id=user.id,
        job_id=job_id,
        job_description=job_description if not job_id else None,
        job_title=job_title,
        company_name=company_name,
        status="generating",
    )
    session.add(prep)
    await session.commit()
    await session.refresh(prep)

    try:
        await _enqueue_interview_prep_job(
            str(prep.id), str(user.id), str(profile.id), job_description
        )
    except Exception as exc:
        logger.error(f"Failed to enqueue ARQ job: {exc}", extra={"prep_id": str(prep.id)})
        prep.status = "failed"
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start interview prep generation. Please try again.",
        )

    logger.info(
        "interview_prep_generation_enqueued",
        extra={
            "user_id": str(user.id),
            "job_id": str(job_id) if job_id else None,
            "prep_id": str(prep.id),
        },
    )

    return InterviewSetupResponse(prep_id=prep.id, status="generating")


@router.get("/preps/{prep_id}/status", response_model=InterviewPrepStatusResponse)
async def get_interview_prep_status(
    prep_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewPrepStatusResponse:
    result = await session.execute(
        select(InterviewPrep).where(InterviewPrep.id == prep_id)
    )
    prep = result.scalar_one_or_none()
    if prep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    await _check_ownership(prep, user)

    question_count = len(prep.questions) if prep.questions else 0
    return InterviewPrepStatusResponse(
        prep_id=prep.id,
        status=prep.status,
        question_count=question_count,
    )


@router.get("/preps", response_model=InterviewPrepListResponse)
async def list_interview_preps(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewPrepListResponse:
    stmt = (
        select(InterviewPrep)
        .where(InterviewPrep.user_id == user.id)
        .order_by(desc(InterviewPrep.created_at))
        .limit(limit)
        .offset(offset)
    )
    results = await session.execute(stmt)
    preps = results.scalars().all()

    count_stmt = (
        select(func.count())
        .select_from(InterviewPrep)
        .where(InterviewPrep.user_id == user.id)
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    items = [
        InterviewPrepListItem(
            id=p.id,
            job_id=p.job_id,
            job_title=p.job_title,
            company_name=p.company_name,
            status=p.status,
            question_count=len(p.questions) if p.questions else 0,
            created_at=p.created_at,
        )
        for p in preps
    ]

    return InterviewPrepListResponse(preps=items, total=total)


@router.post("/chat", response_model=InterviewChatResponse)
async def interview_chat(
    request: InterviewChatRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewChatResponse:
    result = await session.execute(
        select(InterviewPrep).where(InterviewPrep.id == request.prep_id)
    )
    prep = result.scalar_one_or_none()
    if prep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    await _check_ownership(prep, user)

    if prep.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Interview prep is not ready yet. Please wait for question generation to complete.",
        )

    questions = prep.questions or []
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No questions available for this prep.",
        )

    session_obj: InterviewSession
    if request.session_id:
        sess_result = await session.execute(
            select(InterviewSession).where(InterviewSession.id == request.session_id)
        )
        session_obj = sess_result.scalar_one_or_none()
        if session_obj is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found.",
            )
        await _check_session_ownership(session_obj, user)
        if session_obj.status == "completed":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="This session is already completed.",
            )
    else:
        session_obj = InterviewSession(
            user_id=user.id,
            interview_prep_id=prep.id,
            messages=[],
            current_difficulty=1,
            status="active",
            questions_answered=0,
        )
        session.add(session_obj)
        await session.commit()
        await session.refresh(session_obj)

    messages: list[dict] = session_obj.messages or []
    evaluation_data: ChatEvaluation | None = None
    last_score: float | None = None

    if request.answer and messages:
        last_question_msg = None
        for msg in reversed(messages):
            if msg.get("role") == "question":
                last_question_msg = msg
                break

        if last_question_msg:
            pipeline = AIPipeline(ai_client=AIClient())
            job_context = json.dumps({
                "job_title": prep.job_title,
                "company_name": prep.company_name,
                "job_description": prep.job_description,
            })
            coach_eval = await pipeline.evaluate_interview_answer(
                question=last_question_msg["content"],
                answer=request.answer,
                job_context=job_context,
                difficulty=session_obj.current_difficulty,
                context={"user_id": str(user.id), "session_id": str(session_obj.id)},
            )

            evaluation_data = ChatEvaluation(
                score=coach_eval.score,
                strengths=coach_eval.strengths,
                improvements=coach_eval.improvements,
                coaching_tip=coach_eval.coaching_tip,
                sample_answer=coach_eval.sample_answer,
            )
            last_score = coach_eval.score

            messages.append({
                "role": "user",
                "content": request.answer,
                "category": last_question_msg.get("category"),
                "difficulty": last_question_msg.get("difficulty"),
            })
            messages.append({
                "role": "coach",
                "content": json.dumps(coaching_msg_content(coach_eval)),
                "score": coach_eval.score,
                "category": last_question_msg.get("category"),
                "difficulty": last_question_msg.get("difficulty"),
            })
            session_obj.questions_answered = (session_obj.questions_answered or 0) + 1

    next_q = _pick_next_question(
        questions, messages, session_obj.current_difficulty, last_score
    )

    if next_q is None:
        session_obj.status = "completed"
        session_obj.completed_at = datetime.utcnow()
        scores = [m["score"] for m in messages if m.get("role") == "coach" and m.get("score") is not None]
        session_obj.overall_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        pipeline = AIPipeline(ai_client=AIClient())
        job_context = json.dumps({
            "job_title": prep.job_title,
            "company_name": prep.company_name,
        })
        summary = await pipeline.generate_session_summary(
            messages=messages,
            scores=scores,
            context={"user_id": str(user.id), "session_id": str(session_obj.id)},
        )
        messages.append({"role": "summary", "content": summary})

        session_obj.messages = messages
        await session.commit()
        await session.refresh(session_obj)

        return InterviewChatResponse(
            session_id=session_obj.id,
            evaluation=evaluation_data,
            next_question=None,
            session_complete=True,
            difficulty=session_obj.current_difficulty,
            overall_feedback=summary,
        )

    adjusted_diff = next_q.pop("_adjusted_difficulty", session_obj.current_difficulty)
    session_obj.current_difficulty = adjusted_diff

    messages.append({
        "role": "question",
        "content": next_q["question"],
        "category": next_q["category"],
        "difficulty": next_q["difficulty"],
    })
    session_obj.messages = messages
    await session.commit()
    await session.refresh(session_obj)

    return InterviewChatResponse(
        session_id=session_obj.id,
        evaluation=evaluation_data,
        next_question=ChatQuestion(**next_q),
        session_complete=False,
        difficulty=session_obj.current_difficulty,
    )


def coaching_msg_content(eval_result) -> str:
    return (
        f"Score: {eval_result.score}/10\n\n"
        f"**Strengths:**\n"
        + "\n".join(f"- {s}" for s in eval_result.strengths)
        + "\n\n**Improvements:**\n"
        + "\n".join(f"- {i}" for i in eval_result.improvements)
        + f"\n\n**Coaching Tip:** {eval_result.coaching_tip}"
        + f"\n\n**Sample Answer:** {eval_result.sample_answer}"
    )


@router.get("/sessions", response_model=InterviewSessionListResponse)
async def list_interview_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewSessionListResponse:
    stmt = (
        select(
            InterviewSession.id,
            InterviewSession.interview_prep_id,
            InterviewSession.status,
            InterviewSession.questions_answered,
            InterviewSession.overall_score,
            InterviewSession.created_at,
            InterviewPrep.job_title,
            InterviewPrep.company_name,
        )
        .join(InterviewPrep, InterviewSession.interview_prep_id == InterviewPrep.id)
        .where(InterviewSession.user_id == user.id)
        .order_by(desc(InterviewSession.created_at))
        .limit(limit)
        .offset(offset)
    )
    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = (
        select(func.count())
        .select_from(InterviewSession)
        .where(InterviewSession.user_id == user.id)
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    items = [
        InterviewSessionListItem(
            id=row.id,
            prep_id=row.interview_prep_id,
            job_title=row.job_title,
            company_name=row.company_name,
            status=row.status,
            questions_answered=row.questions_answered,
            overall_score=row.overall_score,
            created_at=row.created_at,
        )
        for row in rows
    ]

    return InterviewSessionListResponse(sessions=items, total=total)


@router.get("/sessions/{session_id}", response_model=InterviewSessionDetail)
async def get_interview_session(
    session_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_async_session),
) -> InterviewSessionDetail:
    result = await db_session.execute(
        select(InterviewSession).where(InterviewSession.id == session_id)
    )
    session_obj = result.scalar_one_or_none()
    if session_obj is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    await _check_session_ownership(session_obj, user)

    messages_data = session_obj.messages or []
    session_messages = [
        SessionMessage(
            role=m.get("role", ""),
            content=m.get("content", ""),
            score=m.get("score"),
            category=m.get("category"),
            difficulty=m.get("difficulty"),
        )
        for m in messages_data
    ]

    overall_feedback = None
    for m in reversed(messages_data):
        if m.get("role") == "summary":
            overall_feedback = m.get("content", "")
            break

    return InterviewSessionDetail(
        id=session_obj.id,
        prep_id=session_obj.interview_prep_id,
        status=session_obj.status,
        current_difficulty=session_obj.current_difficulty,
        questions_answered=session_obj.questions_answered,
        overall_score=session_obj.overall_score,
        messages=session_messages,
        overall_feedback=overall_feedback,
        completed_at=session_obj.completed_at,
        created_at=session_obj.created_at,
    )


@router.delete("/preps/{prep_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_interview_prep(
    prep_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    result = await session.execute(
        select(InterviewPrep).where(InterviewPrep.id == prep_id)
    )
    prep = result.scalar_one_or_none()
    if prep is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview prep not found.",
        )
    await _check_ownership(prep, user)

    await session.delete(prep)
    await session.commit()

    logger.info(
        "interview_prep_deleted",
        extra={"prep_id": str(prep_id), "user_id": str(user.id)},
    )
