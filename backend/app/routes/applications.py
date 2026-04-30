import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.application import Application
from app.models.base import ApplicationStatus, JobSource
from app.models.cover_letter import CoverLetter
from app.models.interview import InterviewPrep
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from app.schemas.applications import (
    ApplicationDetail,
    ApplicationJobInfo,
    ApplicationListItem,
    ApplicationListResponse,
    ApplicationNotesUpdate,
    ApplicationStats,
    ApplicationStatusEnum,
    ApplicationUpdate,
)

logger = logging.getLogger(__name__)

VALID_SORT_FIELDS = {"created_at", "updated_at", "applied_at"}

router = APIRouter(prefix="/api/applications", tags=["applications"])


def _job_to_job_info(job: Job) -> ApplicationJobInfo:
    return ApplicationJobInfo(
        id=job.id,
        title=job.title,
        company=job.company,
        location=job.location,
        source=job.source.value if isinstance(job.source, JobSource) else job.source,
        source_url=job.source_url,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        remote_policy=(
            job.remote_policy.value if job.remote_policy else None
        ),
        experience_level=(
            job.experience_level.value if job.experience_level else None
        ),
    )


async def _get_application_with_ownership(
    application_id: uuid.UUID,
    user_id: uuid.UUID,
    session: AsyncSession,
) -> Application:
    result = await session.execute(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found.",
        )
    return application


@router.get("", response_model=ApplicationListResponse)
async def list_applications(
    status_filter: str | None = Query(default=None, alias="status"),
    company: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplicationListResponse:
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field. Allowed: {', '.join(sorted(VALID_SORT_FIELDS))}",
        )

    clauses: list = [Application.user_id == user.id]

    if status_filter:
        try:
            clauses.append(Application.status == ApplicationStatus(status_filter))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid status filter. Allowed: {', '.join(s.value for s in ApplicationStatus)}",
            )

    if company:
        clauses.append(Job.company.ilike(f"%{company}%"))

    stmt = (
        select(
            Application,
            Job,
            JobMatch.match_score,
            Resume.id.label("resume_id"),
            CoverLetter.id.label("cover_letter_id"),
            InterviewPrep.id.label("interview_prep_id"),
        )
        .join(Job, Application.job_id == Job.id)
        .outerjoin(
            JobMatch,
            and_(JobMatch.job_id == Job.id, JobMatch.user_id == user.id),
        )
        .outerjoin(
            Resume,
            and_(Resume.job_id == Job.id, Resume.user_id == user.id),
        )
        .outerjoin(
            CoverLetter,
            and_(CoverLetter.job_id == Job.id, CoverLetter.user_id == user.id),
        )
        .outerjoin(
            InterviewPrep,
            and_(InterviewPrep.job_id == Job.id, InterviewPrep.user_id == user.id),
        )
        .where(and_(*clauses))
    )

    sort_column = getattr(Application, sort_by, Application.created_at)
    stmt = stmt.order_by(desc(sort_column)).limit(limit).offset(offset)

    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = (
        select(func.count())
        .select_from(Application)
        .join(Job, Application.job_id == Job.id)
        .where(and_(*clauses))
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    applications = []
    for app, job, match_score, resume_id, cover_letter_id, interview_prep_id in rows:
        applications.append(
            ApplicationListItem(
                id=app.id,
                status=app.status.value if isinstance(app.status, ApplicationStatus) else app.status,
                applied_at=app.applied_at,
                notes=app.notes,
                created_at=app.created_at,
                updated_at=app.updated_at,
                job=_job_to_job_info(job),
                match_score=match_score,
                resume_id=resume_id,
                cover_letter_id=cover_letter_id,
                interview_prep_id=interview_prep_id,
            )
        )

    logger.info(
        "applications_listed",
        extra={
            "user_id": str(user.id),
            "status_filter": status_filter,
            "result_count": len(applications),
        },
    )

    return ApplicationListResponse(applications=applications, total=total)


@router.get("/stats", response_model=ApplicationStats)
async def get_application_stats(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplicationStats:
    total_result = await session.execute(
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == user.id)
    )
    total = total_result.scalar() or 0

    by_status_result = await session.execute(
        select(Application.status, func.count())
        .where(Application.user_id == user.id)
        .group_by(Application.status)
    )
    by_status = {}
    for status_val, count in by_status_result:
        key = status_val.value if isinstance(status_val, ApplicationStatus) else status_val
        by_status[key] = count

    return ApplicationStats(total=total, by_status=by_status)


@router.get("/{application_id}", response_model=ApplicationDetail)
async def get_application(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplicationDetail:
    application = await _get_application_with_ownership(application_id, user.id, session)

    job_result = await session.execute(select(Job).where(Job.id == application.job_id))
    job = job_result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated job not found.",
        )

    match_score: float | None = None
    match_breakdown: dict | None = None
    match_result = await session.execute(
        select(JobMatch).where(
            and_(JobMatch.user_id == user.id, JobMatch.job_id == application.job_id)
        )
    )
    cached = match_result.scalar_one_or_none()
    if cached:
        match_score = cached.match_score
        match_breakdown = {
            "skills_score": cached.skills_score,
            "experience_score": cached.experience_score,
            "role_relevance_score": cached.role_relevance_score,
            "location_score": cached.location_score,
        }

    resume_result = await session.execute(
        select(Resume.id).where(
            and_(Resume.user_id == user.id, Resume.job_id == application.job_id)
        ).limit(1)
    )
    resume_id = resume_result.scalar_one_or_none()

    cover_letter_result = await session.execute(
        select(CoverLetter.id).where(
            and_(CoverLetter.user_id == user.id, CoverLetter.job_id == application.job_id)
        ).limit(1)
    )
    cover_letter_id = cover_letter_result.scalar_one_or_none()

    interview_prep_result = await session.execute(
        select(InterviewPrep.id).where(
            and_(InterviewPrep.user_id == user.id, InterviewPrep.job_id == application.job_id)
        ).limit(1)
    )
    interview_prep_id = interview_prep_result.scalar_one_or_none()

    return ApplicationDetail(
        id=application.id,
        status=application.status.value if isinstance(application.status, ApplicationStatus) else application.status,
        applied_at=application.applied_at,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        job=_job_to_job_info(job),
        match_score=match_score,
        match_breakdown=match_breakdown,
        resume_id=resume_id,
        cover_letter_id=cover_letter_id,
        interview_prep_id=interview_prep_id,
    )


@router.patch("/{application_id}", response_model=ApplicationDetail)
async def update_application(
    application_id: uuid.UUID,
    update: ApplicationUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplicationDetail:
    application = await _get_application_with_ownership(application_id, user.id, session)

    old_status = application.status

    if update.status is not None:
        application.status = ApplicationStatus(update.status.value)

        if (
            application.status == ApplicationStatus.applied
            and application.applied_at is None
        ):
            application.applied_at = datetime.utcnow()

    if update.notes is not None:
        application.notes = update.notes

    application.updated_at = datetime.utcnow()
    session.add(application)
    await session.commit()
    await session.refresh(application)

    logger.info(
        "application_status_updated",
        extra={
            "user_id": str(user.id),
            "application_id": str(application_id),
            "old_status": old_status.value if isinstance(old_status, ApplicationStatus) else old_status,
            "new_status": application.status.value if isinstance(application.status, ApplicationStatus) else application.status,
        },
    )

    return await get_application(application_id, user, session)


@router.delete("/{application_id}", status_code=status.HTTP_200_OK)
async def delete_application(
    application_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    application = await _get_application_with_ownership(application_id, user.id, session)

    job_id = application.job_id
    await session.delete(application)
    await session.commit()

    logger.info(
        "application_deleted",
        extra={
            "user_id": str(user.id),
            "application_id": str(application_id),
            "job_id": str(job_id),
        },
    )

    return {"message": "Application deleted"}


@router.post("/{application_id}/notes", response_model=ApplicationDetail)
async def update_application_notes(
    application_id: uuid.UUID,
    notes_update: ApplicationNotesUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ApplicationDetail:
    application = await _get_application_with_ownership(application_id, user.id, session)

    application.notes = notes_update.notes
    application.updated_at = datetime.utcnow()
    session.add(application)
    await session.commit()
    await session.refresh(application)

    return await get_application(application_id, user, session)
