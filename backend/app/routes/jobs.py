import logging
import uuid
from datetime import datetime, timedelta, timezone

from arq import create_pool as arq_create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import CurrentUser, get_current_user
from app.config import settings as app_settings
from app.database import get_async_session
from app.models.application import Application
from app.models.base import ApplicationStatus, ExperienceLevel, JobSource, RemotePolicy
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.job_match import JobMatch
from app.schemas.jobs import (
    JobDetailResponse,
    JobDiscoverRequest,
    JobDiscoverResponse,
    JobDiscoverStatusResponse,
    JobListItem,
    JobListResponse,
    MultiSourceDiscoverResponse,
    SavedJobListItem,
    SavedJobsResponse,
    SourceStatusItem,
    SourcesStatusResponse,
)
from app.schemas.match import (
    JobScoreResponse,
    MatchBreakdown,
    MatchRequest,
    MatchResponse,
    MatchStatusResponse,
)
from app.services.match_scorer import MatchScorer

logger = logging.getLogger(__name__)

VALID_SORT_FIELDS = {"match_score", "created_at", "salary_max"}

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _get_redis_settings() -> RedisSettings:
    url = app_settings.REDIS_URL
    host = url.split("@")[-1].split(":")[0] if "@" in url else "localhost"
    port = int(url.split(":")[-1].split("/")[0]) if ":" in url else 6379
    database = int(url.rstrip("/").split("/")[-1]) if "/" in url else 0
    return RedisSettings(host=host, port=port, database=database)


async def _enqueue_linkedin_discovery_job(
    user_id: str,
    keywords: list[str],
    location: str | None,
) -> str:
    redis = await arq_create_pool(_get_redis_settings())
    try:
        job = await redis.enqueue_job(
            "linkedin_discovery_job",
            user_id,
            keywords,
            location,
        )
        return job.job_id if job else ""
    finally:
        await redis.close()


async def _enqueue_api_discovery_job(
    keywords: list[str],
    location: str | None,
    sources: list[str],
) -> str:
    redis = await arq_create_pool(_get_redis_settings())
    try:
        job = await redis.enqueue_job(
            "api_discovery_job",
            keywords,
            location,
            sources,
        )
        return job.job_id if job else ""
    finally:
        await redis.close()


async def _resolve_profile(
    user_id: uuid.UUID,
    session: AsyncSession,
    *,
    load_target_roles: bool = False,
) -> CandidateProfile:
    stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    if load_target_roles:
        stmt = stmt.options(selectinload(CandidateProfile.target_roles))
    result = await session.execute(stmt)
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile and onboarding first.",
        )
    return profile


async def _enqueue_match_job(user_id: str) -> str:
    redis = await arq_create_pool(_get_redis_settings())
    try:
        job = await redis.enqueue_job("match_jobs_job", user_id)
        return job.job_id if job else ""
    finally:
        await redis.close()


@router.post("/discover", response_model=JobDiscoverResponse)
async def discover_jobs(
    request: JobDiscoverRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> JobDiscoverResponse:
    profile = await _resolve_profile(user.id, session, load_target_roles=True)

    try:
        requested_sources = request.validated_sources()
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    needs_linkedin = requested_sources is None or "linkedin" in requested_sources
    api_sources = [s for s in (requested_sources or []) if s != "linkedin"] if requested_sources else []

    if needs_linkedin:
        if not profile.linkedin_email or not profile.linkedin_password_encrypted:
            if requested_sources is not None and len(requested_sources) == 1 and requested_sources[0] == "linkedin":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Save LinkedIn credentials first.",
                )
            needs_linkedin = False

    if needs_linkedin:
        now = datetime.now(timezone.utc)
        if profile.linkedin_last_scraped_at:
            elapsed = now - profile.linkedin_last_scraped_at
            cooldown = timedelta(hours=app_settings.LINKEDIN_SESSION_COOLDOWN_HOURS)
            if elapsed < cooldown:
                remaining = cooldown - elapsed
                remaining_hours = remaining.total_seconds() / 3600
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cooldown active. Try again in {remaining_hours:.1f} hours.",
                )

    keywords = request.keywords
    if not keywords:
        target_roles = [tr.title for tr in profile.target_roles] if profile.target_roles else []
        if not target_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Set your target roles in your profile first.",
            )
        keywords = target_roles

    try:
        if needs_linkedin:
            job_id = await _enqueue_linkedin_discovery_job(
                str(user.id),
                keywords,
                request.location,
            )
        elif api_sources:
            job_id = await _enqueue_api_discovery_job(
                keywords,
                request.location,
                api_sources,
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No discovery sources available. Configure LinkedIn credentials or specify API sources.",
            )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Failed to enqueue discovery job: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start job discovery. Please try again.",
        )

    logger.info(
        "job_discovery_enqueued",
        extra={"user_id": str(user.id), "keywords": keywords, "job_id": job_id},
    )

    return JobDiscoverResponse(
        job_id=job_id,
        message="Discovery started",
    )


@router.get("/discover/status", response_model=JobDiscoverStatusResponse)
async def get_discover_status(
    job_id: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> JobDiscoverStatusResponse:
    last_scraped: str | None = None
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()
    if profile and profile.linkedin_last_scraped_at:
        last_scraped = profile.linkedin_last_scraped_at.isoformat()

    if not job_id:
        return JobDiscoverStatusResponse(status="cooldown", last_scraped_at=last_scraped)

    try:
        redis = await arq_create_pool(_get_redis_settings())
        from arq.jobs import Job as ArqJob

        arq_job = ArqJob(job_id, redis=redis)
        info = await arq_job.info()
        await redis.close()

        if info is None:
            return JobDiscoverStatusResponse(status="unknown", last_scraped_at=last_scraped)

        if info.result is not None:
            job_status = "completed"
        elif info.started is not None:
            job_status = "running"
        else:
            job_status = "pending"

    except Exception:
        job_status = "unknown"

    return JobDiscoverStatusResponse(status=job_status, last_scraped_at=last_scraped)


@router.get("/sources/status", response_model=SourcesStatusResponse)
async def get_sources_status(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SourcesStatusResponse:
    profile_result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()

    has_linkedin = bool(profile and profile.linkedin_email and profile.linkedin_password_encrypted)

    from app.services.job_sources import ADAPTER_REGISTRY

    sources: list[SourceStatusItem] = [
        SourceStatusItem(
            name="linkedin",
            type="scrape",
            available=has_linkedin,
            detail="Requires saved LinkedIn credentials" if not has_linkedin else None,
        ),
    ]

    for name, adapter_cls in ADAPTER_REGISTRY.items():
        adapter = adapter_cls()
        headers = adapter.build_headers()
        params = adapter.build_params("test", None) or {}
        has_key = bool(
            headers and any(v for v in headers.values())
        ) or bool(
            params and any(
                k.endswith("_key") or k.endswith("_id") or k == "api_key"
                for k, v in params.items() if v
            )
        )

        sources.append(SourceStatusItem(
            name=name,
            type="api",
            available=has_key,
            detail=f"Requires {name.capitalize()} API key" if not has_key else None,
        ))

    return SourcesStatusResponse(sources=sources)


def _job_list_filters(
    source: str | None,
    search: str | None,
    experience_level: str | None,
    job_type: str | None,
    remote_policy: str | None,
) -> list[object]:
    clauses: list[object] = []
    if source:
        try:
            clauses.append(Job.source == JobSource(source))
        except ValueError:
            pass
    if search:
        escaped = escape_ilike(search)
        clauses.append(
            or_(
                Job.title.ilike(f"%{escaped}%"),
                Job.company.ilike(f"%{escaped}%"),
            )
        )
    if experience_level:
        try:
            clauses.append(Job.experience_level == ExperienceLevel(experience_level))
        except ValueError:
            pass
    if job_type:
        clauses.append(Job.job_type == job_type)
    if remote_policy:
        try:
            clauses.append(Job.remote_policy == RemotePolicy(remote_policy))
        except ValueError:
            pass
    return clauses


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    source: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=200),
    experience_level: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    remote_policy: str | None = Query(default=None),
    sort_by: str = Query(default="created_at"),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> JobListResponse:
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort field. Allowed: {', '.join(sorted(VALID_SORT_FIELDS))}",
        )

    clauses = _job_list_filters(source, search, experience_level, job_type, remote_policy)

    stmt = select(Job, JobMatch.match_score, Application.id).outerjoin(
        JobMatch,
        and_(JobMatch.job_id == Job.id, JobMatch.user_id == user.id),
    ).outerjoin(
        Application,
        and_(Application.job_id == Job.id, Application.user_id == user.id, Application.status == ApplicationStatus.saved),
    )
    if clauses:
        stmt = stmt.where(and_(*clauses))

    if sort_by == "match_score":
        stmt = stmt.order_by(JobMatch.match_score.desc().nulls_last())
    elif sort_by == "salary_max":
        stmt = stmt.order_by(Job.salary_max.desc().nulls_last())
    else:
        stmt = stmt.order_by(desc(Job.created_at))

    stmt = stmt.limit(limit).offset(offset)

    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = select(func.count()).select_from(Job)
    if clauses:
        count_stmt = count_stmt.where(and_(*clauses))

    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    return JobListResponse(
        jobs=[
            JobListItem(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                source=job.source.value if isinstance(job.source, JobSource) else job.source,
                source_url=job.source_url,
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                experience_level=job.experience_level.value if job.experience_level else None,
                job_type=job.job_type,
                remote_policy=job.remote_policy.value if job.remote_policy else None,
                scraped_at=job.scraped_at,
                created_at=job.created_at,
                match_score=match_score,
                is_saved=app_id is not None,
            )
            for job, match_score, app_id in rows
        ],
        total=total,
    )


@router.get("/saved", response_model=SavedJobsResponse)
async def list_saved_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SavedJobsResponse:
    stmt = (
        select(Application, Job)
        .join(Job, Application.job_id == Job.id)
        .where(
            Application.user_id == user.id,
            Application.status == ApplicationStatus.saved,
        )
        .order_by(desc(Application.created_at))
        .limit(limit)
        .offset(offset)
    )
    results = await session.execute(stmt)
    rows = results.all()

    count_stmt = (
        select(func.count())
        .select_from(Application)
        .where(
            Application.user_id == user.id,
            Application.status == ApplicationStatus.saved,
        )
    )
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0

    return SavedJobsResponse(
        jobs=[
            SavedJobListItem(
                application_id=app.id,
                job_id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                source=job.source.value if isinstance(job.source, JobSource) else job.source,
                saved_at=app.created_at,
            )
            for app, job in rows
        ],
        total=total,
    )


@router.post("/match", response_model=MatchResponse)
async def match_jobs(
    request: MatchRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MatchResponse:
    await _resolve_profile(user.id, session)

    try:
        task_id = await _enqueue_match_job(str(user.id))
    except Exception as exc:
        logger.error(f"Failed to enqueue match job: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to start job matching. Please try again.",
        )

    logger.info(
        "match_job_enqueued",
        extra={"user_id": str(user.id), "task_id": task_id},
    )

    return MatchResponse(task_id=task_id, message="Matching started")


@router.get("/match/status", response_model=MatchStatusResponse)
async def get_match_status(
    task_id: str | None = Query(default=None),
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MatchStatusResponse:
    if not task_id:
        total_result = await session.execute(select(func.count()).select_from(JobMatch).where(JobMatch.user_id == user.id))
        scored_count = total_result.scalar() or 0
        return MatchStatusResponse(status="unknown", scored_count=scored_count, total_count=0)

    try:
        redis = await arq_create_pool(_get_redis_settings())
        from arq.jobs import Job as ArqJob

        arq_job = ArqJob(task_id, redis=redis)
        info = await arq_job.info()
        await redis.close()

        if info is None:
            return MatchStatusResponse(status="unknown", scored_count=0, total_count=0)

        if info.result is not None:
            job_status = "completed"
        elif info.started is not None:
            job_status = "in_progress"
        else:
            job_status = "pending"

    except Exception:
        job_status = "unknown"

    total_result = await session.execute(select(func.count()).select_from(JobMatch).where(JobMatch.user_id == user.id))
    scored_count = total_result.scalar() or 0

    return MatchStatusResponse(status=job_status, scored_count=scored_count, total_count=0)


@router.get("/{job_id}/score", response_model=JobScoreResponse)
async def get_job_score(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> JobScoreResponse:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    scorer = MatchScorer(session)
    cached = await scorer.get_cached_score(user.id, job_id)

    if cached is not None:
        return JobScoreResponse(
            job_id=cached.job_id,
            match_score=cached.match_score,
            breakdown=MatchBreakdown(
                skills_score=cached.skills_score,
                experience_score=cached.experience_score,
                role_relevance_score=cached.role_relevance_score,
                location_score=cached.location_score,
            ),
            matched_skills=cached.matched_skills,
            missing_skills=cached.missing_skills,
        )

    match_result = await scorer.score_job(user.id, job_id)
    if match_result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Complete your profile and onboarding first.",
        )

    return JobScoreResponse(
        job_id=match_result.job_id,
        match_score=match_result.match_score,
        breakdown=MatchBreakdown(
            skills_score=match_result.skills_score,
            experience_score=match_result.experience_score,
            role_relevance_score=match_result.role_relevance_score,
            location_score=match_result.location_score,
        ),
        matched_skills=match_result.matched_skills,
        missing_skills=match_result.missing_skills,
    )


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> JobDetailResponse:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    match_score: float | None = None
    match_breakdown = None
    is_saved = False

    match_result = await session.execute(
        select(JobMatch).where(
            and_(JobMatch.user_id == user.id, JobMatch.job_id == job_id)
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

    saved_result = await session.execute(
        select(Application.id).where(
            and_(
                Application.user_id == user.id,
                Application.job_id == job_id,
                Application.status == ApplicationStatus.saved,
            )
        )
    )
    if saved_result.scalar_one_or_none():
        is_saved = True

    return JobDetailResponse(
        id=job.id,
        source=job.source.value if isinstance(job.source, JobSource) else job.source,
        source_url=job.source_url,
        external_id=job.external_id,
        title=job.title,
        company=job.company,
        description=job.description,
        salary_min=job.salary_min,
        salary_max=job.salary_max,
        salary_currency=job.salary_currency,
        location=job.location,
        experience_level=job.experience_level.value if job.experience_level else None,
        job_type=job.job_type,
        remote_policy=job.remote_policy.value if job.remote_policy else None,
        ats_platform=job.ats_platform,
        apply_url=job.apply_url,
        scraped_at=job.scraped_at,
        created_at=job.created_at,
        alternate_sources=job.alternate_sources,
        match_score=match_score,
        match_breakdown=match_breakdown,
        is_saved=is_saved,
    )


@router.post("/{job_id}/save", status_code=status.HTTP_200_OK)
async def save_job(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found.",
        )

    existing = await session.execute(
        select(Application).where(
            Application.user_id == user.id,
            Application.job_id == job_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already saved.",
        )

    application = Application(
        user_id=user.id,
        job_id=job_id,
        status=ApplicationStatus.saved,
    )
    session.add(application)
    await session.commit()

    if job.apply_url:
        try:
            redis = await arq_create_pool(_get_redis_settings())
            await redis.enqueue_job(
                "ats_detect_job",
                str(application.id),
                str(user.id),
                job.apply_url,
                _job_id=f"ats_detect_{application.id}",
            )
            await redis.close()
            logger.info(
                "auto_ats_detect_enqueued",
                extra={"user_id": str(user.id), "job_id": str(job_id), "application_id": str(application.id)},
            )
        except Exception as exc:
            logger.warning(f"Failed to enqueue auto ATS detection: {exc}")

    logger.info(
        "job_saved",
        extra={"user_id": str(user.id), "job_id": str(job_id)},
    )

    return {"message": "Job saved"}


@router.delete("/{job_id}/save", status_code=status.HTTP_200_OK)
async def unsave_job(
    job_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    result = await session.execute(
        select(Application).where(
            Application.user_id == user.id,
            Application.job_id == job_id,
            Application.status == ApplicationStatus.saved,
        )
    )
    application = result.scalar_one_or_none()
    if application is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Saved job not found.",
        )

    await session.delete(application)
    await session.commit()

    logger.info(
        "job_unsaved",
        extra={"user_id": str(user.id), "job_id": str(job_id)},
    )

    return {"message": "Job unsaved"}
