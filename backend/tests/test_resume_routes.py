import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.resume import Resume
from tests.conftest import mint_jwt


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


async def _setup_user_with_profile(client: AsyncClient, user_id: str | None = None) -> tuple[str, str]:
    uid = user_id or str(uuid.uuid4())
    token = mint_jwt(user_id=uid)
    headers = {"Authorization": f"Bearer {token}"}

    # Create profile via sync-profile
    sync_resp = await client.post("/api/auth/sync-profile", headers=headers)
    assert sync_resp.status_code == 200

    # Complete onboarding
    onboarding_payload = {
        "personal_info": {
            "first_name": "Test",
            "last_name": "User",
            "headline": "Software Engineer",
            "experience_level": "senior",
        },
        "target_roles": [{"title": "Backend Engineer", "priority": 1}],
        "skills": [{"name": "Python", "category": "Programming", "proficiency": "expert"}],
        "education": [],
        "experience": [],
    }
    save_resp = await client.post(
        "/api/onboarding/save", json=onboarding_payload, headers=headers
    )
    assert save_resp.status_code == 200
    profile_id = save_resp.json()["profile_id"]

    return token, profile_id


async def _create_completed_resume(
    session: AsyncSession,
    user_id: str,
    job_id: str | None = None,
    ats_score: float = 85.0,
) -> Resume:
    resume = Resume(
        user_id=uuid.UUID(user_id),
        job_id=uuid.UUID(job_id) if job_id else None,
        status="completed",
        content_json={"sections": []},
        ats_score=ats_score,
        ats_breakdown={"overall_score": ats_score},
    )
    session.add(resume)
    await session.commit()
    await session.refresh(resume)
    return resume


async def _create_job(session: AsyncSession) -> Job:
    job = Job(
        source="linkedin",
        title="Senior Backend Engineer",
        company="Acme Corp",
        description="We are looking for a senior backend engineer with Python and FastAPI experience. The ideal candidate has 5+ years of experience building scalable systems.",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


# ---- Happy Path Tests ----


@pytest.mark.asyncio
async def test_get_profile_me():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)

        response = await client.get(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "Test"
    assert data["last_name"] == "User"
    assert data["onboarding_completed"] is True
    assert data["experience_level"] == "senior"


@pytest.mark.asyncio
async def test_list_resumes():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/sync-profile", headers=headers)

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            for i in range(3):
                await _create_completed_resume(session, user_id, str(job.id))

        response = await client.get("/api/resumes", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["resumes"]) == 3


@pytest.mark.asyncio
async def test_list_resumes_empty():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/resumes", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["resumes"] == []


@pytest.mark.asyncio
async def test_get_resume_by_id():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            resume = await _create_completed_resume(session, user_id, str(job.id))

        response = await client.get(f"/api/resumes/{resume.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["ats_score"] == 85.0
    assert data["status"] == "completed"
    assert data["content_json"] is not None


@pytest.mark.asyncio
async def test_delete_resume():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            resume = await _create_completed_resume(session, user_id)
            resume_id = str(resume.id)

        response = await client.delete(f"/api/resumes/{resume_id}", headers=headers)

    assert response.status_code == 204

    async with factory() as session:
        from sqlalchemy import select
        result = await session.execute(select(Resume).where(Resume.id == resume_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_get_resume_status():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            resume = await _create_completed_resume(session, user_id)
            resume_id = str(resume.id)

        response = await client.get(f"/api/resumes/{resume_id}/status", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["ats_score"] == 85.0


# ---- Failure Path Tests ----


@pytest.mark.asyncio
async def test_generate_resume_no_profile():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/resumes/generate-manual",
            json={
                "job_description": "A" * 100,
            },
            headers=headers,
        )

    assert response.status_code == 404
    assert "profile" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_resume_not_onboarded():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create profile but don't complete onboarding
        await client.post("/api/auth/sync-profile", headers=headers)

        response = await client.post(
            "/api/resumes/generate-manual",
            json={
                "job_description": "A" * 100,
            },
            headers=headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_resume_not_owner():
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    token_a = mint_jwt(user_id=user_a_id)
    token_b = mint_jwt(user_id=user_b_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            resume = await _create_completed_resume(session, user_a_id)
            resume_id = str(resume.id)

        # User B tries to delete user A's resume
        response = await client.delete(
            f"/api/resumes/{resume_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_resumes_pagination():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            for _ in range(25):
                await _create_completed_resume(session, user_id)

        response = await client.get("/api/resumes?limit=10&offset=0", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 25
    assert len(data["resumes"]) == 10

    # Second page
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response2 = await client.get("/api/resumes?limit=10&offset=10", headers=headers)

    assert response2.status_code == 200
    data2 = response2.json()
    assert data2["total"] == 25
    assert len(data2["resumes"]) == 10


@pytest.mark.asyncio
async def test_get_profile_me_no_profile():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/profile/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_resume_with_job_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Create a job in the DB
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            job_id = str(job.id)

        with patch("app.routes.resumes._enqueue_resume_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/resumes/generate",
                json={"job_id": job_id},
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"
    assert "resume_id" in data


@pytest.mark.asyncio
async def test_generate_resume_manual():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.routes.resumes._enqueue_resume_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/resumes/generate-manual",
                json={
                    "job_description": "We are looking for a senior backend engineer with Python experience. Must have 5+ years building scalable APIs.",
                    "company_name": "Test Corp",
                    "job_title": "Backend Engineer",
                },
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"
    assert "resume_id" in data


@pytest.mark.asyncio
async def test_generate_resume_dedup_guard():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client, user_id)
        headers = {"Authorization": f"Bearer {token}"}

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            job_id = str(job.id)
            # Create an existing completed resume
            existing = await _create_completed_resume(session, user_id, job_id)

        response = await client.post(
            "/api/resumes/generate",
            json={"job_id": job_id},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["resume_id"] == str(existing.id)
