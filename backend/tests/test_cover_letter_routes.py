import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.cover_letter import CoverLetter
from app.models.job import Job
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

    sync_resp = await client.post("/api/auth/sync-profile", headers=headers)
    assert sync_resp.status_code == 200

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


async def _create_completed_cover_letter(
    session: AsyncSession,
    user_id: str,
    job_id: str | None = None,
    tone: str = "professional",
) -> CoverLetter:
    cover_letter = CoverLetter(
        user_id=uuid.UUID(user_id),
        job_id=uuid.UUID(job_id) if job_id else None,
        status="completed",
        content="Dear Hiring Manager, I am writing to express my interest...",
        content_json={
            "paragraphs": [{"heading": None, "body": "Dear Hiring Manager..."}],
            "tone_used": tone,
            "keywords_addressed": ["Python", "FastAPI"],
            "full_text": "Dear Hiring Manager, I am writing to express my interest...",
        },
        tone=tone,
        ai_model_used="glm-4-plus",
    )
    session.add(cover_letter)
    await session.commit()
    await session.refresh(cover_letter)
    return cover_letter


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
async def test_generate_cover_letter_with_job_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            job_id = str(job.id)

        with patch("app.routes.cover_letters._enqueue_cover_letter_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/cover-letters/generate",
                json={"job_id": job_id},
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"
    assert "cover_letter_id" in data


@pytest.mark.asyncio
async def test_generate_cover_letter_with_job_description():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.routes.cover_letters._enqueue_cover_letter_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/cover-letters/generate",
                json={
                    "job_description": "We are looking for a senior backend engineer with Python experience. Must have 5+ years building scalable APIs.",
                },
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"
    assert "cover_letter_id" in data


@pytest.mark.asyncio
async def test_generate_cover_letter_dedup():
    user_id = str(uuid.uuid4())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client, user_id)
        headers = {"Authorization": f"Bearer {token}"}

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            job_id = str(job.id)
            existing = await _create_completed_cover_letter(session, user_id, job_id)

        response = await client.post(
            "/api/cover-letters/generate",
            json={"job_id": job_id},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["cover_letter_id"] == str(existing.id)


@pytest.mark.asyncio
async def test_generate_cover_letter_job_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/cover-letters/generate",
            json={"job_id": str(uuid.uuid4())},
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_generate_cover_letter_no_profile():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/cover-letters/generate-manual",
            json={"job_description": "A" * 100},
            headers=headers,
        )

    assert response.status_code == 404
    assert "profile" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_generate_cover_letter_onboarding_incomplete():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/auth/sync-profile", headers=headers)

        response = await client.post(
            "/api/cover-letters/generate-manual",
            json={"job_description": "A" * 100},
            headers=headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_cover_letter_status():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            cl = await _create_completed_cover_letter(session, user_id)

        response = await client.get(
            f"/api/cover-letters/{cl.id}/status",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["tone"] == "professional"


@pytest.mark.asyncio
async def test_get_cover_letter_status_not_found():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            f"/api/cover-letters/{uuid.uuid4()}/status",
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_cover_letters():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            for _ in range(3):
                await _create_completed_cover_letter(session, user_id, str(job.id))

        response = await client.get("/api/cover-letters", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["cover_letters"]) == 3


@pytest.mark.asyncio
async def test_get_cover_letter_detail():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            cl = await _create_completed_cover_letter(session, user_id, str(job.id))

        response = await client.get(f"/api/cover-letters/{cl.id}", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["content"] is not None
    assert data["tone"] == "professional"


@pytest.mark.asyncio
async def test_get_cover_letter_detail_generating():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            cl = CoverLetter(
                user_id=uuid.UUID(user_id),
                status="generating",
                tone="professional",
            )
            session.add(cl)
            await session.commit()
            await session.refresh(cl)

        response = await client.get(f"/api/cover-letters/{cl.id}", headers=headers)

    assert response.status_code == 202


@pytest.mark.asyncio
async def test_delete_cover_letter():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            cl = await _create_completed_cover_letter(session, user_id)
            cl_id = str(cl.id)

        response = await client.delete(f"/api/cover-letters/{cl_id}", headers=headers)

    assert response.status_code == 204

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(CoverLetter).where(CoverLetter.id == cl_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_cover_letter_unauthorized():
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    token_b = mint_jwt(user_id=user_b_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            cl = await _create_completed_cover_letter(session, user_a_id)
            cl_id = str(cl.id)

        response = await client.delete(
            f"/api/cover-letters/{cl_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_cover_letter_generate_request_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        # Neither job_id nor job_description provided
        response = await client.post(
            "/api/cover-letters/generate",
            json={},
            headers=headers,
        )

    assert response.status_code == 422
