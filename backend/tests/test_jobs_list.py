import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.application import Application
from app.models.base import ApplicationStatus, JobSource, RemotePolicy
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


@pytest.mark.asyncio
async def test_list_jobs_returns_is_saved_false_when_not_saved():
    transport = ASGITransport(app=app)
    job = None
    async for session in _get_test_session():
        job = await _create_test_job(session)
        break

    assert job is not None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/jobs",
            params={"search": job.title},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    matched = [j for j in jobs if j["id"] == str(job.id)]
    assert len(matched) == 1
    assert matched[0]["is_saved"] is False


@pytest.mark.asyncio
async def test_list_jobs_returns_is_saved_true_after_saving():
    transport = ASGITransport(app=app)
    job = None
    async for session in _get_test_session():
        job = await _create_test_job(session)
        break

    assert job is not None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        save_resp = await client.post(
            f"/api/jobs/{job.id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert save_resp.status_code == 200

        resp = await client.get(
            "/api/jobs",
            params={"search": job.title},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    matched = [j for j in jobs if j["id"] == str(job.id)]
    assert len(matched) == 1
    assert matched[0]["is_saved"] is True


@pytest.mark.asyncio
async def test_list_jobs_search_filters_by_title():
    transport = ASGITransport(app=app)
    unique_title = f"UniqueSearchTitle-{uuid.uuid4().hex[:8]}"
    async for session in _get_test_session():
        await _create_test_job(session, title=unique_title)
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/jobs",
            params={"search": unique_title},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) >= 1
    assert all(unique_title in j["title"] for j in jobs)


@pytest.mark.asyncio
async def test_list_jobs_filter_by_source():
    transport = ASGITransport(app=app)
    unique_title = f"SourceFilter-{uuid.uuid4().hex[:8]}"
    async for session in _get_test_session():
        await _create_test_job(session, title=unique_title, source=JobSource.adzuna)
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/jobs",
            params={"search": unique_title, "source": "adzuna"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) >= 1


@pytest.mark.asyncio
async def test_list_jobs_filter_by_remote_policy():
    transport = ASGITransport(app=app)
    unique_title = f"RemoteFilter-{uuid.uuid4().hex[:8]}"
    async for session in _get_test_session():
        await _create_test_job(session, title=unique_title, remote_policy=RemotePolicy.remote)
        break

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/jobs",
            params={"search": unique_title, "remote_policy": "remote"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert len(jobs) >= 1


@pytest.mark.asyncio
async def test_list_jobs_search_max_length_rejected():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        long_search = "a" * 201
        resp = await client.get(
            "/api/jobs",
            params={"search": long_search},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_job_detail_returns_is_saved():
    transport = ASGITransport(app=app)
    job = None
    async for session in _get_test_session():
        job = await _create_test_job(session)
        break

    assert job is not None
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)

        detail_resp = await client.get(
            f"/api/jobs/{job.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["is_saved"] is False

        save_resp = await client.post(
            f"/api/jobs/{job.id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert save_resp.status_code == 200

        detail_resp2 = await client.get(
            f"/api/jobs/{job.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert detail_resp2.status_code == 200
        assert detail_resp2.json()["is_saved"] is True
