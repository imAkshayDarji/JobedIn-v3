"""
E2E flow test: register -> onboard -> discover -> match -> generate resume -> save job -> apply.

Exercises the full API chain using httpx AsyncClient against the FastAPI app.
External services (Redis/arq, AI pipeline, Playwright) are mocked.
Database uses the real test PostgreSQL via the existing conftest pattern.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.application import Application
from app.models.base import ApplicationStatus, ExperienceLevel, JobSource, RemotePolicy
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from tests.conftest import TEST_JWT_SECRET, mint_jwt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _get_test_session():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _override_db_and_rate_limit():
    app.dependency_overrides[get_async_session] = _get_test_session
    from app.middleware.rate_limit import limiter

    limiter.enabled = False
    yield
    app.dependency_overrides.clear()
    limiter.enabled = settings.RATE_LIMIT_ENABLED


@pytest.fixture()
def user_id() -> str:
    return str(uuid.uuid4())


@pytest.fixture()
def auth_headers(user_id: str) -> dict[str, str]:
    token = mint_jwt(user_id=user_id)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_job(session: AsyncSession) -> Job:
    job = Job(
        source=JobSource.adzuna,
        source_url="https://example.com/job/123",
        external_id=f"e2e-{uuid.uuid4()}",
        title="Senior Python Developer",
        company="E2E Corp",
        description="We are looking for a senior Python developer with FastAPI and PostgreSQL experience. Remote-friendly. Must have experience with async programming, Docker, and CI/CD pipelines.",
        salary_min=120000,
        salary_max=180000,
        location="Remote",
        experience_level=ExperienceLevel.senior,
        job_type="Full-time",
        remote_policy=RemotePolicy.remote,
        apply_url="https://example.com/job/123/apply",
        scraped_at=datetime.now(timezone.utc),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _seed_resume(
    session: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> Resume:
    resume = Resume(
        user_id=user_id,
        job_id=job_id,
        status="completed",
        content_json={
            "sections": [
                {"type": "summary", "content": "Experienced Python developer"},
                {"type": "experience", "content": "Senior Developer at E2E Corp"},
            ]
        },
        ats_score=87.5,
        ats_breakdown={"keyword_density": 0.85, "section_completeness": 0.90},
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def _seed_match(
    session: AsyncSession, user_id: uuid.UUID, job_id: uuid.UUID
) -> JobMatch:
    match = JobMatch(
        user_id=user_id,
        job_id=job_id,
        match_score=82.0,
        skills_score=85.0,
        experience_score=90.0,
        role_relevance_score=80.0,
        location_score=70.0,
        matched_skills=["Python", "FastAPI", "PostgreSQL"],
        missing_skills=["Kubernetes"],
        scored_at=datetime.now(timezone.utc),
    )
    session.add(match)
    await session.commit()
    await session.refresh(match)
    return match


# ---------------------------------------------------------------------------
# E2E test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_user_journey(user_id: str, auth_headers: dict[str, str]):
    """
    Full E2E: auth sync -> onboarding -> job discovery (seeded) ->
    match scoring (seeded) -> resume generation (seeded) ->
    save job -> application tracker -> status update.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ── Step 1: Sync profile (equivalent to post-registration) ──
        resp = await client.post("/api/auth/sync-profile", headers=auth_headers)
        assert resp.status_code == 200, f"sync-profile failed: {resp.text}"
        sync_data = resp.json()
        assert sync_data["status"] == "created"
        profile_id = sync_data["profile_id"]

        # ── Step 2: Check onboarding status (should be 0%) ──
        resp = await client.get("/api/onboarding/status", headers=auth_headers)
        assert resp.status_code == 200, f"onboarding status failed: {resp.text}"
        status_data = resp.json()
        assert status_data["completion_percentage"] == 0
        assert status_data["onboarding_completed"] is False

        # ── Step 3: Complete onboarding ──
        onboarding_payload = {
            "personal_info": {
                "first_name": "Jane",
                "last_name": "Developer",
                "headline": "Senior Software Engineer",
                "summary": "Experienced full-stack developer specializing in Python and React.",
                "location": "San Francisco, CA",
                "experience_level": "senior",
                "linkedin_url": "https://linkedin.com/in/janedeveloper",
                "github_url": "https://github.com/janedeveloper",
            },
            "target_roles": [
                {"title": "Senior Python Developer", "priority": 1, "keywords": "python, fastapi, postgresql"},
                {"title": "Full-Stack Engineer", "priority": 2, "keywords": "react, typescript, node"},
            ],
            "skills": [
                {"name": "Python", "category": "Programming", "proficiency": "expert"},
                {"name": "FastAPI", "category": "Framework", "proficiency": "advanced"},
                {"name": "PostgreSQL", "category": "Database", "proficiency": "advanced"},
                {"name": "Docker", "category": "DevOps", "proficiency": "intermediate"},
                {"name": "React", "category": "Frontend", "proficiency": "intermediate"},
            ],
            "education": [
                {
                    "institution": "University of Technology",
                    "degree": "Bachelor of Science",
                    "field_of_study": "Computer Science",
                }
            ],
            "experience": [
                {
                    "company": "TechStartup Inc",
                    "title": "Senior Developer",
                    "location": "San Francisco, CA",
                    "is_current": True,
                    "description": "Built microservices with FastAPI and PostgreSQL.",
                }
            ],
        }
        resp = await client.post(
            "/api/onboarding/save",
            json=onboarding_payload,
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"onboarding save failed: {resp.text}"
        save_data = resp.json()
        assert save_data["profile_id"] == profile_id
        assert save_data["created_target_roles"] == 2
        assert save_data["created_skills"] == 5
        assert save_data["created_education"] == 1
        assert save_data["created_experience"] == 1

        # ── Step 4: Verify onboarding complete ──
        resp = await client.get("/api/onboarding/status", headers=auth_headers)
        assert resp.status_code == 200
        status_data = resp.json()
        assert status_data["onboarding_completed"] is True
        assert status_data["completion_percentage"] == 100

        # ── Step 5: Discover jobs (mock Redis/arq enqueue) ──
        with patch("app.routes.jobs.arq_create_pool", new_callable=AsyncMock) as mock_pool:
            mock_redis = AsyncMock()
            mock_redis.enqueue_job = AsyncMock(return_value="fake-task-id")
            mock_redis.close = AsyncMock()
            mock_pool.return_value = mock_redis

            resp = await client.post(
                "/api/jobs/discover",
                json={"sources": ["adzuna"]},
                headers=auth_headers,
            )
        assert resp.status_code == 200, f"discover failed: {resp.text}"
        discover_data = resp.json()
        assert "job_id" in discover_data
        assert discover_data["message"] == "Discovery started"

        # ── Step 6: Seed a discovered job directly (simulate worker output) ──
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as db_session:
            job = await _seed_job(db_session)
            job_id = str(job.id)

        # ── Step 7: Verify job appears in listing ──
        resp = await client.get("/api/jobs", headers=auth_headers)
        assert resp.status_code == 200, f"jobs list failed: {resp.text}"
        jobs_data = resp.json()
        assert jobs_data["total"] >= 1
        listed_ids = [j["id"] for j in jobs_data["items"]]
        assert job_id in listed_ids

        # ── Step 8: Match scoring (mock Redis/arq enqueue) ──
        with patch("app.routes.jobs.arq_create_pool", new_callable=AsyncMock) as mock_pool:
            mock_redis = AsyncMock()
            mock_redis.enqueue_job = AsyncMock(return_value="match-task-id")
            mock_redis.close = AsyncMock()
            mock_pool.return_value = mock_redis

            resp = await client.post(
                "/api/jobs/match",
                json={},
                headers=auth_headers,
            )
        assert resp.status_code == 200, f"match failed: {resp.text}"

        # ── Step 9: Seed match score (simulate worker output) ──
        async with factory() as db_session:
            await _seed_match(db_session, uuid.UUID(user_id), job.id)

        # ── Step 10: Verify job detail has match score ──
        resp = await client.get(f"/api/jobs/{job_id}", headers=auth_headers)
        assert resp.status_code == 200, f"job detail failed: {resp.text}"
        job_detail = resp.json()
        assert job_detail["title"] == "Senior Python Developer"
        assert job_detail["match_score"] == 82.0
        assert "match_breakdown" in job_detail

        # ── Step 11: Generate resume (mock Redis/arq enqueue) ──
        with patch("app.routes.resumes.arq_create_pool", new_callable=AsyncMock) as mock_pool:
            mock_redis = AsyncMock()
            mock_redis.enqueue_job = AsyncMock(return_value="resume-task-id")
            mock_redis.close = AsyncMock()
            mock_pool.return_value = mock_redis

            resp = await client.post(
                "/api/resumes/generate",
                json={"job_id": job_id},
                headers=auth_headers,
            )
        assert resp.status_code == 200, f"resume generate failed: {resp.text}"
        resume_data = resp.json()
        assert resume_data["status"] == "generating"
        resume_id = resume_data["resume_id"]

        # ── Step 12: Seed completed resume (simulate worker output) ──
        async with factory() as db_session:
            # Delete the generating resume first, then add completed one
            result = await db_session.execute(
                select(Resume).where(Resume.id == uuid.UUID(str(resume_id)))
            )
            existing_resume = result.scalar_one_or_none()
            if existing_resume:
                existing_resume.status = "completed"
                existing_resume.content_json = {
                    "sections": [
                        {"type": "summary", "content": "Experienced Python developer"},
                        {"type": "experience", "content": "Senior Developer at TechStartup Inc"},
                    ]
                }
                existing_resume.ats_score = 87.5
                await db_session.commit()
                await db_session.refresh(existing_resume)

        # ── Step 13: Verify resume exists ──
        resp = await client.get(f"/api/resumes/{resume_id}", headers=auth_headers)
        assert resp.status_code == 200, f"resume detail failed: {resp.text}"
        resume_detail = resp.json()
        assert resume_detail["status"] == "completed"
        assert resume_detail["ats_score"] == 87.5

        # ── Step 14: Save job (creates Application) ──
        with patch("app.routes.jobs.arq_create_pool", new_callable=AsyncMock):
            resp = await client.post(
                f"/api/jobs/{job_id}/save",
                headers=auth_headers,
            )
        assert resp.status_code == 200, f"save job failed: {resp.text}"

        # ── Step 15: Verify application in tracker ──
        resp = await client.get("/api/applications", headers=auth_headers)
        assert resp.status_code == 200, f"applications list failed: {resp.text}"
        apps_data = resp.json()
        assert apps_data["total"] >= 1
        application = apps_data["items"][0]
        assert application["status"] == "saved"
        assert application["job"]["title"] == "Senior Python Developer"
        application_id = application["id"]

        # ── Step 16: Update application status to "ready" ──
        resp = await client.patch(
            f"/api/applications/{application_id}",
            json={"status": "ready"},
            headers=auth_headers,
        )
        assert resp.status_code == 200, f"update application failed: {resp.text}"
        updated_app = resp.json()
        assert updated_app["status"] == "ready"

        # ── Step 17: Verify dashboard reflects the state ──
        resp = await client.get("/api/dashboard", headers=auth_headers)
        assert resp.status_code == 200, f"dashboard failed: {resp.text}"
        dashboard = resp.json()
        assert dashboard["stats"]["applications"] >= 1
        assert dashboard["stats"]["resumes"] >= 1
        assert dashboard["stats"]["jobs_matched"] >= 1

        # Cleanup
        await engine.dispose()
