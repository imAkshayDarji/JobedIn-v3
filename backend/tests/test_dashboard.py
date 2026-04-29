import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.application import Application
from app.models.base import ApplicationStatus, JobSource
from app.models.candidate import CandidateProfile
from app.models.cover_letter import CoverLetter
from app.models.interview import InterviewPrep, InterviewSession
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.resume import Resume
from tests.conftest import TEST_JWT_SECRET, mint_jwt
from tests.test_resume_routes import _setup_user_with_profile


async def _get_test_session():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture(autouse=True)
def _override_db():
    app.dependency_overrides[get_async_session] = _get_test_session
    yield
    app.dependency_overrides.clear()


async def _create_test_job(session: AsyncSession, **overrides) -> Job:
    defaults = {
        "source": JobSource.jsearch,
        "external_id": f"test-{uuid.uuid4().hex[:12]}",
        "title": f"TestJob-{uuid.uuid4().hex[:8]}",
        "company": "TestCo",
        "description": "A test job",
    }
    defaults.update(overrides)
    job = Job(**defaults)
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


# ── Auth ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_unauthenticated_returns_401():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/dashboard")
    assert resp.status_code == 401


# ── Empty / no profile ───────────────────────────────


@pytest.mark.asyncio
async def test_no_profile_returns_200_with_zeroed_stats():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())
    token = mint_jwt(user_id=uid)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"] is None
    assert body["stats"]["jobs_matched"] == 0
    assert body["recent_activity"] == []


@pytest.mark.asyncio
async def test_empty_user_all_counts_zero_avgs_null():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["applications_count"] == 0
    assert stats["resumes_count"] == 0
    assert stats["cover_letters_count"] == 0
    assert stats["interview_sessions_count"] == 0
    assert stats["avg_ats_score"] is None
    assert stats["avg_match_score"] is None
    assert stats["avg_session_score"] is None


# ── With data ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_correct_counts_with_data():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job1 = await _create_test_job(session, title="DataJob1")
        job2 = await _create_test_job(session, title="DataJob2")
        job3 = await _create_test_job(session, title="DataJob3")
        session.add(Application(
            user_id=uuid.UUID(uid),
            job_id=job1.id,
            status=ApplicationStatus.saved,
        ))
        session.add(Application(
            user_id=uuid.UUID(uid),
            job_id=job2.id,
            status=ApplicationStatus.applied,
        ))
        session.add(Application(
            user_id=uuid.UUID(uid),
            job_id=job3.id,
            status=ApplicationStatus.saved,
        ))
        for _ in range(2):
            session.add(Resume(
                user_id=uuid.UUID(uid),
                status="completed",
                ats_score=80.0,
            ))
        session.add(CoverLetter(
            user_id=uuid.UUID(uid),
            job_id=job1.id,
            status="completed",
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["applications_count"] == 3
    assert stats["resumes_count"] == 2
    assert stats["cover_letters_count"] == 1


@pytest.mark.asyncio
async def test_applications_by_status():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job1 = await _create_test_job(session, title="StatusJob1")
        job2 = await _create_test_job(session, title="StatusJob2")
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job1.id, status=ApplicationStatus.saved,
        ))
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job2.id, status=ApplicationStatus.applied,
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    by_status = resp.json()["stats"]["applications_by_status"]
    assert by_status.get("saved", 0) == 1
    assert by_status.get("applied", 0) == 1


@pytest.mark.asyncio
async def test_applications_count_total():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job1 = await _create_test_job(session, title="CountJob1")
        job2 = await _create_test_job(session, title="CountJob2")
        job3 = await _create_test_job(session, title="CountJob3")
        statuses = [ApplicationStatus.saved, ApplicationStatus.applied, ApplicationStatus.rejected]
        for j, status in zip([job1, job2, job3], statuses):
            session.add(Application(
                user_id=uuid.UUID(uid), job_id=j.id, status=status,
            ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["stats"]["applications_count"] == 3


@pytest.mark.asyncio
async def test_match_stats():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job1 = await _create_test_job(session, title="MatchJob1")
        job2 = await _create_test_job(session, title="MatchJob2")
        from datetime import datetime as _dt

        session.add(JobMatch(
            user_id=uuid.UUID(uid), job_id=job1.id,
            match_score=85.0, skills_score=80.0, experience_score=90.0,
            role_relevance_score=85.0, location_score=80.0,
            scored_at=_dt.utcnow(),
        ))
        session.add(JobMatch(
            user_id=uuid.UUID(uid), job_id=job2.id,
            match_score=50.0, skills_score=50.0, experience_score=50.0,
            role_relevance_score=50.0, location_score=50.0,
            scored_at=_dt.utcnow(),
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    stats = resp.json()["stats"]
    assert stats["jobs_matched"] == 2
    assert stats["high_match_count"] == 1
    assert stats["avg_match_score"] == 67.5


@pytest.mark.asyncio
async def test_avg_ats_score_from_completed_resumes():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        session.add(Resume(
            user_id=uuid.UUID(uid), status="completed", ats_score=80.0,
        ))
        session.add(Resume(
            user_id=uuid.UUID(uid), status="completed", ats_score=90.0,
        ))
        session.add(Resume(
            user_id=uuid.UUID(uid), status="generating", ats_score=None,
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["stats"]["avg_ats_score"] == 85.0


@pytest.mark.asyncio
async def test_avg_session_score():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        prep = InterviewPrep(
            user_id=uuid.UUID(uid),
            status="completed",
            job_title="Engineer",
        )
        session.add(prep)
        await session.commit()
        await session.refresh(prep)

        session.add(InterviewSession(
            user_id=uuid.UUID(uid),
            interview_prep_id=prep.id,
            status="completed",
            overall_score=75.0,
        ))
        session.add(InterviewSession(
            user_id=uuid.UUID(uid),
            interview_prep_id=prep.id,
            status="completed",
            overall_score=85.0,
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["stats"]["avg_session_score"] == 80.0


# ── Activity ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_activity_ordering_most_recent_first():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job = await _create_test_job(session, title="OrderedJob")
        job2 = await _create_test_job(session, title="OrderedJob2")
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job.id, status=ApplicationStatus.saved,
        ))
        session.add(CoverLetter(
            user_id=uuid.UUID(uid), job_id=job2.id, status="completed",
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    activity = resp.json()["recent_activity"]
    assert len(activity) >= 2
    for i in range(len(activity) - 1):
        assert activity[i]["created_at"] >= activity[i + 1]["created_at"]


@pytest.mark.asyncio
async def test_activity_types_all_four():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job = await _create_test_job(session)
        job2 = await _create_test_job(session, title="TypeJob2")
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job.id, status=ApplicationStatus.saved,
        ))
        session.add(Resume(user_id=uuid.UUID(uid), status="completed"))
        session.add(CoverLetter(
            user_id=uuid.UUID(uid), job_id=job2.id, status="completed",
        ))
        prep = InterviewPrep(
            user_id=uuid.UUID(uid), status="completed", job_title="Dev",
        )
        session.add(prep)
        await session.commit()
        await session.refresh(prep)
        session.add(InterviewSession(
            user_id=uuid.UUID(uid),
            interview_prep_id=prep.id,
            status="active",
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    activity = resp.json()["recent_activity"]
    types_present = {item["type"] for item in activity}
    assert "application" in types_present
    assert "resume" in types_present
    assert "cover_letter" in types_present
    assert "interview_session" in types_present


@pytest.mark.asyncio
async def test_activity_titles_format():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())
    job_title = f"TitleTest-{uuid.uuid4().hex[:6]}"

    async for session in _get_test_session():
        job = await _create_test_job(session, title=job_title)
        job2 = await _create_test_job(session, title=job_title + "2")
        job3 = await _create_test_job(session, title=job_title + "3")
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job.id, status=ApplicationStatus.saved,
        ))
        session.add(Resume(
            user_id=uuid.UUID(uid), job_id=job2.id, status="completed",
        ))
        session.add(CoverLetter(
            user_id=uuid.UUID(uid), job_id=job3.id, status="completed",
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    activity = resp.json()["recent_activity"]
    by_type = {item["type"]: item for item in activity}

    assert by_type["application"]["title"] == job_title
    assert job_title + "2" in by_type["resume"]["title"]
    assert job_title + "3" in by_type["cover_letter"]["title"]


@pytest.mark.asyncio
async def test_activity_job_id_on_application_items():
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())

    async for session in _get_test_session():
        job = await _create_test_job(session)
        session.add(Application(
            user_id=uuid.UUID(uid), job_id=job.id, status=ApplicationStatus.saved,
        ))
        await session.commit()
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client, user_id=uid)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    activity = resp.json()["recent_activity"]
    apps = [a for a in activity if a["type"] == "application"]
    assert len(apps) >= 1
    assert apps[0]["job_id"] is not None


# ── Profile ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_profile_summary():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    profile = resp.json()["profile"]
    assert profile is not None
    assert profile["first_name"] == "Test"
    assert profile["experience_level"] == "senior"
    assert profile["onboarding_completed"] is True
