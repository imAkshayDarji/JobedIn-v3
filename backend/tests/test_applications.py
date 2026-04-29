import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.application import Application
from app.models.base import ApplicationStatus, JobSource
from app.models.job import Job
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


async def _create_job(session: AsyncSession) -> Job:
    job = Job(
        source=JobSource.linkedin,
        external_id=f"app-test-{uuid.uuid4().hex[:12]}",
        title=f"AppTestJob-{uuid.uuid4().hex[:8]}",
        company=f"AppTestCo-{uuid.uuid4().hex[:4]}",
        description="Test job for application tests",
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return job


async def _create_application(
    session: AsyncSession,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    status: ApplicationStatus = ApplicationStatus.saved,
) -> Application:
    application = Application(
        user_id=user_id,
        job_id=job_id,
        status=status,
    )
    session.add(application)
    await session.commit()
    await session.refresh(application)
    return application


async def _get_user_id_from_token(token: str) -> uuid.UUID:
    import jwt

    payload = jwt.decode(
        token,
        TEST_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )
    return uuid.UUID(str(payload["sub"]))


# ── GET /api/applications ─────────────────────────────────────


@pytest.mark.asyncio
async def test_list_applications():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            await _create_application(session, uid, job.id)
            break

        resp = await client.get("/api/applications", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "applications" in data
        assert "total" in data
        assert data["total"] >= 1


@pytest.mark.asyncio
async def test_list_applications_filter_by_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job1 = await _create_job(session)
            job2 = await _create_job(session)
            await _create_application(session, uid, job1.id, ApplicationStatus.saved)
            await _create_application(session, uid, job2.id, ApplicationStatus.applied)
            break

        resp = await client.get(
            "/api/applications",
            params={"status": "applied"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert all(a["status"] == "applied" for a in data["applications"])


@pytest.mark.asyncio
async def test_list_applications_search_by_company():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            await _create_application(session, uid, job.id)
            company_name = job.company
            break

        resp = await client.get(
            "/api/applications",
            params={"company": company_name},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert data["applications"][0]["job"]["company"] == company_name


@pytest.mark.asyncio
async def test_list_applications_pagination():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            "/api/applications",
            params={"limit": 1, "offset": 0},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["applications"]) <= 1


# ── GET /api/applications/stats ───────────────────────────────


@pytest.mark.asyncio
async def test_get_application_stats_with_data():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            await _create_application(session, uid, job.id)
            break

        resp = await client.get("/api/applications/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert "by_status" in data
        assert "saved" in data["by_status"]


@pytest.mark.asyncio
async def test_get_application_stats_empty():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/applications/stats", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["by_status"] == {}


# ── GET /api/applications/{id} ────────────────────────────────


@pytest.mark.asyncio
async def test_get_application_detail():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        resp = await client.get(
            f"/api/applications/{app_id}", headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(app_id)
        assert data["job"]["title"] == job.title
        assert "match_score" in data
        assert "match_breakdown" in data


@pytest.mark.asyncio
async def test_get_application_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/applications/{fake_id}", headers=headers
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_application_wrong_user():
    transport = ASGITransport(app=app)
    app_id: uuid.UUID | None = None

    async for session in _get_test_session():
        job = await _create_job(session)
        user_id = uuid.uuid4()
        app_obj = await _create_application(session, user_id, job.id)
        app_id = app_obj.id
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            f"/api/applications/{app_id}", headers=headers
        )
        assert resp.status_code == 404


# ── PATCH /api/applications/{id} ──────────────────────────────


@pytest.mark.asyncio
async def test_update_application_status():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        resp = await client.patch(
            f"/api/applications/{app_id}",
            json={"status": "applied"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "applied"
        assert data["applied_at"] is not None


@pytest.mark.asyncio
async def test_update_application_notes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        resp = await client.patch(
            f"/api/applications/{app_id}",
            json={"notes": "Need to follow up by Friday"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Need to follow up by Friday"


@pytest.mark.asyncio
async def test_update_application_applied_at_auto_set():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            assert app_obj.applied_at is None
            break

        resp = await client.patch(
            f"/api/applications/{app_id}",
            json={"status": "applied"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["applied_at"] is not None


@pytest.mark.asyncio
async def test_update_application_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = str(uuid.uuid4())
        resp = await client.patch(
            f"/api/applications/{fake_id}",
            json={"status": "applied"},
            headers=headers,
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_application_wrong_user():
    transport = ASGITransport(app=app)
    app_id: uuid.UUID | None = None

    async for session in _get_test_session():
        job = await _create_job(session)
        user_id = uuid.uuid4()
        app_obj = await _create_application(session, user_id, job.id)
        app_id = app_obj.id
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.patch(
            f"/api/applications/{app_id}",
            json={"status": "applied"},
            headers=headers,
        )
        assert resp.status_code == 404


# ── DELETE /api/applications/{id} ─────────────────────────────


@pytest.mark.asyncio
async def test_delete_application():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        resp = await client.delete(
            f"/api/applications/{app_id}", headers=headers
        )
        assert resp.status_code == 200

        verify = await client.get(
            f"/api/applications/{app_id}", headers=headers
        )
        assert verify.status_code == 404


@pytest.mark.asyncio
async def test_delete_application_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        fake_id = str(uuid.uuid4())
        resp = await client.delete(
            f"/api/applications/{fake_id}", headers=headers
        )
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_application_wrong_user():
    transport = ASGITransport(app=app)
    app_id: uuid.UUID | None = None

    async for session in _get_test_session():
        job = await _create_job(session)
        user_id = uuid.uuid4()
        app_obj = await _create_application(session, user_id, job.id)
        app_id = app_obj.id
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete(
            f"/api/applications/{app_id}", headers=headers
        )
        assert resp.status_code == 404


# ── POST /api/applications/{id}/notes ─────────────────────────


@pytest.mark.asyncio
async def test_set_application_notes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        resp = await client.post(
            f"/api/applications/{app_id}/notes",
            json={"notes": "Initial note"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Initial note"


@pytest.mark.asyncio
async def test_update_application_notes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        uid = await _get_user_id_from_token(token)
        headers = {"Authorization": f"Bearer {token}"}

        async for session in _get_test_session():
            job = await _create_job(session)
            app_obj = await _create_application(session, uid, job.id)
            app_id = app_obj.id
            break

        await client.post(
            f"/api/applications/{app_id}/notes",
            json={"notes": "First note"},
            headers=headers,
        )

        resp = await client.post(
            f"/api/applications/{app_id}/notes",
            json={"notes": "Updated note"},
            headers=headers,
        )
        assert resp.status_code == 200
        assert resp.json()["notes"] == "Updated note"


# ── Auth ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_applications_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/applications")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_application_requires_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        fake_id = str(uuid.uuid4())
        resp = await client.get(f"/api/applications/{fake_id}")
        assert resp.status_code == 401


# ── Sort ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_applications_sort_by_created_at_desc():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get(
            "/api/applications",
            params={"sort_by": "created_at"},
            headers=headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        apps = data["applications"]
        if len(apps) >= 2:
            from datetime import datetime

            first = datetime.fromisoformat(apps[0]["created_at"])
            second = datetime.fromisoformat(apps[1]["created_at"])
            assert first >= second
