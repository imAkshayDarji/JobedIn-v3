import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.interview import InterviewPrep, InterviewSession
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


async def _create_job(session: AsyncSession) -> Job:
    job = Job(
        source="linkedin",
        title="Senior Backend Engineer",
        company="Acme Corp",
        description="We are looking for a senior backend engineer with Python and FastAPI experience.",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _create_completed_prep(
    session: AsyncSession,
    user_id: str,
    job_id: str | None = None,
) -> InterviewPrep:
    questions = [
        {"question": f"Q{i+1}", "category": cat, "difficulty": diff, "follow_up_hints": []}
        for cat in ["company_research", "technical", "behavioral", "culture_fit"]
        for diff in [1, 2, 3]
        for i in range(1)
    ]
    prep = InterviewPrep(
        user_id=uuid.UUID(user_id),
        job_id=uuid.UUID(job_id) if job_id else None,
        status="completed",
        questions=questions,
        job_title="Senior Backend Engineer",
        company_name="Acme Corp",
    )
    session.add(prep)
    await session.commit()
    await session.refresh(prep)
    return prep


# ---- Setup Tests ----


@pytest.mark.asyncio
async def test_setup_with_job_id():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            job = await _create_job(session)
            job_id = str(job.id)

        with patch("app.routes.interview._enqueue_interview_prep_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/interview/setup",
                json={"job_id": job_id},
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"
    assert "prep_id" in data


@pytest.mark.asyncio
async def test_setup_with_manual_jd():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("app.routes.interview._enqueue_interview_prep_job", new_callable=AsyncMock):
            response = await client.post(
                "/api/interview/setup",
                json={
                    "job_description": "We need a senior engineer with Python and cloud experience.",
                    "job_title": "Cloud Engineer",
                    "company_name": "CloudCorp",
                },
                headers=headers,
            )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "generating"


@pytest.mark.asyncio
async def test_setup_validation_neither_job_id_nor_jd():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, profile_id = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/interview/setup",
            json={},
            headers=headers,
        )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_setup_dedup_returns_existing():
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
            existing = await _create_completed_prep(session, user_id, job_id)

        response = await client.post(
            "/api/interview/setup",
            json={"job_id": job_id},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["prep_id"] == str(existing.id)


# ---- Status Polling ----


@pytest.mark.asyncio
async def test_get_prep_status():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_id)

        response = await client.get(
            f"/api/interview/preps/{prep.id}/status",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["question_count"] == 12


# ---- List Preps ----


@pytest.mark.asyncio
async def test_list_preps():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            await _create_completed_prep(session, user_id)
            await _create_completed_prep(session, user_id)

        response = await client.get("/api/interview/preps", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["preps"]) == 2


# ---- Chat Tests ----


@pytest.mark.asyncio
async def test_chat_first_turn_creates_session():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_id)
            prep_id = str(prep.id)

        response = await client.post(
            "/api/interview/chat",
            json={"prep_id": prep_id},
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] is not None
    assert data["next_question"] is not None
    assert data["session_complete"] is False
    assert data["evaluation"] is None


@pytest.mark.asyncio
async def test_chat_prep_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        response = await client.post(
            "/api/interview/chat",
            json={"prep_id": str(uuid.uuid4()), "answer": "test"},
            headers=headers,
        )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_chat_prep_still_generating():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = InterviewPrep(
                user_id=uuid.UUID(user_id),
                status="generating",
                job_title="Engineer",
                company_name="Corp",
            )
            session.add(prep)
            await session.commit()
            await session.refresh(prep)
            prep_id = str(prep.id)

        response = await client.post(
            "/api/interview/chat",
            json={"prep_id": prep_id, "answer": "test"},
            headers=headers,
        )

    assert response.status_code == 422
    assert "not ready" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_chat_ownership_check():
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    token_b = mint_jwt(user_id=user_b_id)
    headers_b = {"Authorization": f"Bearer {token_b}"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_a_id)

        response = await client.post(
            "/api/interview/chat",
            json={"prep_id": str(prep.id), "answer": "test"},
            headers=headers_b,
        )

    assert response.status_code == 403


# ---- Session Tests ----


@pytest.mark.asyncio
async def test_list_sessions():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_id)
            for _ in range(2):
                sess = InterviewSession(
                    user_id=uuid.UUID(user_id),
                    interview_prep_id=prep.id,
                    messages=[],
                    current_difficulty=1,
                    status="active",
                    questions_answered=0,
                )
                session.add(sess)
            await session.commit()

        response = await client.get("/api/interview/sessions", headers=headers)

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["sessions"]) == 2


@pytest.mark.asyncio
async def test_get_session_detail():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_id)
            sess = InterviewSession(
                user_id=uuid.UUID(user_id),
                interview_prep_id=prep.id,
                messages=[
                    {"role": "question", "content": "Tell me about yourself?", "category": "behavioral", "difficulty": 1},
                    {"role": "user", "content": "I am a software engineer.", "category": "behavioral", "difficulty": 1},
                    {"role": "coach", "content": "Score: 6/10", "score": 6.0, "category": "behavioral", "difficulty": 1},
                ],
                current_difficulty=1,
                status="active",
                questions_answered=1,
            )
            session.add(sess)
            await session.commit()
            await session.refresh(sess)
            session_id = str(sess.id)

        response = await client.get(
            f"/api/interview/sessions/{session_id}",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["questions_answered"] == 1
    assert len(data["messages"]) == 3


# ---- Delete Test ----


@pytest.mark.asyncio
async def test_delete_prep():
    user_id = str(uuid.uuid4())
    token = mint_jwt(user_id=user_id)
    headers = {"Authorization": f"Bearer {token}"}
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_id)
            prep_id = str(prep.id)

        response = await client.delete(
            f"/api/interview/preps/{prep_id}",
            headers=headers,
        )

    assert response.status_code == 204

    async with factory() as session:
        from sqlalchemy import select

        result = await session.execute(select(InterviewPrep).where(InterviewPrep.id == prep_id))
        assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_prep_unauthorized():
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    token_b = mint_jwt(user_id=user_b_id)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        engine = create_async_engine(settings.DATABASE_URL, echo=False)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        async with factory() as session:
            prep = await _create_completed_prep(session, user_a_id)
            prep_id = str(prep.id)

        response = await client.delete(
            f"/api/interview/preps/{prep_id}",
            headers={"Authorization": f"Bearer {token_b}"},
        )

    assert response.status_code == 403
