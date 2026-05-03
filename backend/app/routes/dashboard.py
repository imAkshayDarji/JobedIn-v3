import logging
import time
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.application import Application
from app.models.candidate import CandidateProfile
from app.models.cover_letter import CoverLetter
from app.models.interview import InterviewPrep, InterviewSession
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    DashboardStats,
    ProfileSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


async def _get_profile(
    user_id: uuid.UUID,
    session: AsyncSession,
) -> ProfileSummary | None:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        return None
    return ProfileSummary(
        first_name=profile.first_name,
        experience_level=(
            profile.experience_level.value if profile.experience_level else None
        ),
        onboarding_completed=profile.onboarding_completed,
    )


async def _count(
    session: AsyncSession,
    stmt: select,
) -> int:
    result = await session.execute(stmt)
    return result.scalar() or 0


async def _avg(
    session: AsyncSession,
    stmt: select,
) -> float | None:
    result = await session.execute(stmt)
    val = result.scalar()
    if val is None:
        return None
    return round(float(val), 1)


async def _status_counts(
    session: AsyncSession,
    stmt: select,
) -> dict[str, int]:
    result = await session.execute(stmt)
    rows = result.all()
    return {row[0]: row[1] for row in rows}


async def _get_stats(
    user_id: uuid.UUID,
    session: AsyncSession,
) -> DashboardStats:
    uid = user_id

    try:
        jobs_matched = await _count(
            session,
            select(func.count()).select_from(JobMatch).where(JobMatch.user_id == uid),
        )
        high_match_count = await _count(
            session,
            select(func.count())
            .select_from(JobMatch)
            .where(JobMatch.user_id == uid, JobMatch.match_score >= 70),
        )
        avg_match_score = await _avg(
            session,
            select(func.avg(JobMatch.match_score)).where(JobMatch.user_id == uid),
        )
        applications_count = await _count(
            session,
            select(func.count())
            .select_from(Application)
            .where(Application.user_id == uid),
        )
        applications_by_status = await _status_counts(
            session,
            select(Application.status, func.count())
            .where(Application.user_id == uid)
            .group_by(Application.status),
        )
        resumes_count = await _count(
            session,
            select(func.count())
            .select_from(Resume)
            .where(Resume.user_id == uid),
        )
        resumes_completed = await _count(
            session,
            select(func.count())
            .select_from(Resume)
            .where(Resume.user_id == uid, Resume.status == "completed"),
        )
        avg_ats_score = await _avg(
            session,
            select(func.avg(Resume.ats_score)).where(
                Resume.user_id == uid,
                Resume.ats_score.isnot(None),
            ),
        )
        cover_letters_count = await _count(
            session,
            select(func.count())
            .select_from(CoverLetter)
            .where(CoverLetter.user_id == uid),
        )
        interview_preps_count = await _count(
            session,
            select(func.count())
            .select_from(InterviewPrep)
            .where(InterviewPrep.user_id == uid),
        )
        interview_sessions_count = await _count(
            session,
            select(func.count())
            .select_from(InterviewSession)
            .where(InterviewSession.user_id == uid),
        )
        interview_sessions_completed = await _count(
            session,
            select(func.count())
            .select_from(InterviewSession)
            .where(
                InterviewSession.user_id == uid,
                InterviewSession.status == "completed",
            ),
        )
        avg_session_score = await _avg(
            session,
            select(func.avg(InterviewSession.overall_score)).where(
                InterviewSession.user_id == uid,
                InterviewSession.overall_score.isnot(None),
            ),
        )
    except Exception:
        logger.warning(
            "dashboard.stats_failure",
            extra={"user_id": str(uid)},
            exc_info=True,
        )
        raise

    return DashboardStats(
        jobs_matched=jobs_matched,
        high_match_count=high_match_count,
        avg_match_score=avg_match_score,
        applications_count=applications_count,
        applications_by_status=applications_by_status,
        resumes_count=resumes_count,
        resumes_completed=resumes_completed,
        avg_ats_score=avg_ats_score,
        cover_letters_count=cover_letters_count,
        interview_preps_count=interview_preps_count,
        interview_sessions_count=interview_sessions_count,
        interview_sessions_completed=interview_sessions_completed,
        avg_session_score=avg_session_score,
    )


async def _get_recent_activity(
    user_id: uuid.UUID,
    session: AsyncSession,
) -> list[ActivityItem]:
    uid = user_id
    limit = 10

    items: list[ActivityItem] = []

    try:
        app_result = await session.execute(
            select(Application, Job.title)
            .join(Job, Application.job_id == Job.id, isouter=True)
            .where(Application.user_id == uid)
            .order_by(desc(Application.created_at))
            .limit(limit)
        )
        for app, job_title in app_result.all():
            items.append(
                ActivityItem(
                    type="application",
                    id=str(app.id),
                    title=job_title or "Unknown Job",
                    status=app.status.value if app.status else None,
                    job_id=str(app.job_id),
                    created_at=app.created_at,
                )
            )
    except Exception:
        logger.warning("dashboard.activity_failure", extra={"user_id": str(uid), "type": "application"})

    try:
        resume_result = await session.execute(
            select(Resume, Job.title)
            .join(Job, Resume.job_id == Job.id, isouter=True)
            .where(Resume.user_id == uid)
            .order_by(desc(Resume.created_at))
            .limit(limit)
        )
        for resume, job_title in resume_result.all():
            label = f"Resume for {job_title}" if job_title else "Resume"
            items.append(
                ActivityItem(
                    type="resume",
                    id=str(resume.id),
                    title=label,
                    status=resume.status,
                    job_id=str(resume.job_id) if resume.job_id else None,
                    created_at=resume.created_at,
                )
            )
    except Exception:
        logger.warning("dashboard.activity_failure", extra={"user_id": str(uid), "type": "resume"})

    try:
        cl_result = await session.execute(
            select(CoverLetter, Job.title)
            .join(Job, CoverLetter.job_id == Job.id, isouter=True)
            .where(CoverLetter.user_id == uid)
            .order_by(desc(CoverLetter.created_at))
            .limit(limit)
        )
        for cl, job_title in cl_result.all():
            label = f"Cover letter for {job_title}" if job_title else "Cover Letter"
            items.append(
                ActivityItem(
                    type="cover_letter",
                    id=str(cl.id),
                    title=label,
                    status=cl.status,
                    job_id=str(cl.job_id) if cl.job_id else None,
                    created_at=cl.created_at,
                )
            )
    except Exception:
        logger.warning("dashboard.activity_failure", extra={"user_id": str(uid), "type": "cover_letter"})

    try:
        session_result = await session.execute(
            select(InterviewSession, InterviewPrep.job_title)
            .join(InterviewPrep, InterviewSession.interview_prep_id == InterviewPrep.id)
            .where(InterviewSession.user_id == uid)
            .order_by(desc(InterviewSession.created_at))
            .limit(limit)
        )
        for session_item, job_title in session_result.all():
            label = (
                f"Interview for {job_title}" if job_title else "Interview Practice"
            )
            items.append(
                ActivityItem(
                    type="interview_session",
                    id=str(session_item.id),
                    title=label,
                    status=session_item.status,
                    job_id=None,
                    created_at=session_item.created_at,
                )
            )
    except Exception:
        logger.warning("dashboard.activity_failure", extra={"user_id": str(uid), "type": "interview_session"})

    from datetime import datetime
    items.sort(key=lambda item: item.created_at or datetime.min, reverse=True)
    return items[:limit]


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> DashboardResponse:
    start = time.monotonic()

    logger.info(
        "dashboard.request",
        extra={"user_id": str(user.id)},
    )

    profile = await _get_profile(user.id, session)
    stats = await _get_stats(user.id, session)
    activity = await _get_recent_activity(user.id, session)

    elapsed = (time.monotonic() - start) * 1000
    logger.info(
        "dashboard.response",
        extra={
            "user_id": str(user.id),
            "latency_ms": round(elapsed, 1),
            "activity_count": len(activity),
        },
    )

    return DashboardResponse(
        profile=profile,
        stats=stats,
        recent_activity=activity,
    )
