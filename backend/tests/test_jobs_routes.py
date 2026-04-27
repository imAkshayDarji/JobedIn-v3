import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.base import JobSource
from app.models.candidate import CandidateProfile
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


async def _fernet_key(monkeypatch: pytest.MonkeyPatch) -> str:
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)
    return key


@pytest.mark.asyncio
async def test_discover_requires_profile(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    uid = str(uuid.uuid4())
    token = mint_jwt(user_id=uid)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/jobs/discover",
            json={"keywords": ["Python"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "profile" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_discover_requires_linkedin_credentials(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.post(
            "/api/jobs/discover",
            json={"keywords": ["Python"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "LinkedIn" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_discover_respects_cooldown(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        payload = jwt.decode(
            token,
            TEST_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        uid = uuid.UUID(str(payload["sub"]))

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            profile.linkedin_email = "a@b.com"
            fernet = Fernet(settings.ENCRYPTION_KEY.encode())
            profile.linkedin_password_encrypted = fernet.encrypt(b"x").decode()
            profile.linkedin_last_scraped_at = datetime.now(timezone.utc)
            session.add(profile)
            await session.commit()
            break

        resp = await client.post(
            "/api/jobs/discover",
            json={"keywords": ["Python"]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400
    assert "Cooldown" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_discover_enqueues_job(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        await client.post(
            "/api/settings/linkedin-credentials",
            json={"email": "li@example.com", "password": "pw"},
            headers={"Authorization": f"Bearer {token}"},
        )

        payload = jwt.decode(
            token,
            TEST_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        uid = uuid.UUID(str(payload["sub"]))

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            profile.linkedin_last_scraped_at = datetime.now(timezone.utc) - timedelta(
                hours=settings.LINKEDIN_SESSION_COOLDOWN_HOURS + 1
            )
            session.add(profile)
            await session.commit()
            break

        with patch(
            "app.routes.jobs._enqueue_linkedin_discovery_job",
            new_callable=AsyncMock,
            return_value="test-arq-job-id",
        ):
            resp = await client.post(
                "/api/jobs/discover",
                json={"keywords": ["Rust"]},
                headers={"Authorization": f"Bearer {token}"},
            )
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == "test-arq-job-id"
    assert data["message"] == "Discovery started"


@pytest.mark.asyncio
async def test_discover_uses_target_roles_when_keywords_omitted(
    monkeypatch: pytest.MonkeyPatch,
):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        await client.post(
            "/api/settings/linkedin-credentials",
            json={"email": "li@example.com", "password": "pw"},
            headers={"Authorization": f"Bearer {token}"},
        )

        payload = jwt.decode(
            token,
            TEST_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
        uid = uuid.UUID(str(payload["sub"]))

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            profile.linkedin_last_scraped_at = datetime.now(timezone.utc) - timedelta(
                hours=settings.LINKEDIN_SESSION_COOLDOWN_HOURS + 1
            )
            session.add(profile)
            await session.commit()
            break

        with patch(
            "app.routes.jobs._enqueue_linkedin_discovery_job",
            new_callable=AsyncMock,
        ) as mock_enqueue:
            mock_enqueue.return_value = "jid-2"
            resp = await client.post(
                "/api/jobs/discover",
                json={},
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 200
        mock_enqueue.assert_awaited_once()
        keywords_arg = mock_enqueue.await_args[0][1]
        assert isinstance(keywords_arg, list)
        assert len(keywords_arg) >= 1
        assert "Backend Engineer" in keywords_arg


@pytest.mark.asyncio
async def test_discover_status_without_job_id(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.get(
            "/api/jobs/discover/status",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json()["status"] == "cooldown"


@pytest.mark.asyncio
async def test_list_and_get_and_save_job(monkeypatch: pytest.MonkeyPatch):
    await _fernet_key(monkeypatch)
    transport = ASGITransport(app=app)
    job_id: uuid.UUID | None = None
    unique_title = f"ListTestJob-{uuid.uuid4().hex[:8]}"
    async for session in _get_test_session():
        job = Job(
            source=JobSource.linkedin,
            external_id=f"unit-{uuid.uuid4().hex[:12]}",
            title=unique_title,
            company="Co",
            description="Desc",
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        job_id = job.id
        break

    assert job_id is not None

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        lst = await client.get(
            "/api/jobs",
            params={"search": unique_title},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert lst.status_code == 200
        jobs = lst.json()["jobs"]
        assert any(str(j["id"]) == str(job_id) for j in jobs)

        one = await client.get(
            f"/api/jobs/{job_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert one.status_code == 200
        assert one.json()["title"] == unique_title

        save = await client.post(
            f"/api/jobs/{job_id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert save.status_code == 200

        dup = await client.post(
            f"/api/jobs/{job_id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert dup.status_code == 409

        saved = await client.get(
            "/api/jobs/saved",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert saved.status_code == 200
        assert saved.json()["total"] >= 1

        unsave = await client.delete(
            f"/api/jobs/{job_id}/save",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert unsave.status_code == 200


@pytest.mark.asyncio
async def test_jobs_routes_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/jobs")
        assert r.status_code == 401
