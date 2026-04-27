import uuid
from datetime import datetime, timezone

import jwt
import pytest
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app
from app.models.candidate import CandidateProfile
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


@pytest.mark.asyncio
async def test_save_linkedin_credentials_requires_encryption_key(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        resp = await client.post(
            "/api/settings/linkedin-credentials",
            json={"email": "u@example.com", "password": "secret"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 500


@pytest.mark.asyncio
async def test_save_and_status_and_delete_linkedin_credentials(
    monkeypatch: pytest.MonkeyPatch,
):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)

        save = await client.post(
            "/api/settings/linkedin-credentials",
            json={"email": "linkedin@example.com", "password": "my-password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert save.status_code == 200

        status = await client.get(
            "/api/settings/linkedin-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status.status_code == 200
        body = status.json()
        assert body["has_credentials"] is True
        assert body["email"] == "linkedin@example.com"
        assert "password" not in body
        assert body.get("last_scraped_at") is None

        payload = jwt.decode(token, options={"verify_signature": False})
        uid = uuid.UUID(str(payload["sub"]))

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            assert profile.linkedin_email == "linkedin@example.com"
            assert profile.linkedin_password_encrypted is not None
            assert profile.linkedin_password_encrypted != "my-password"
            break

        delete = await client.delete(
            "/api/settings/linkedin-credentials",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert delete.status_code == 200

        status2 = await client.get(
            "/api/settings/linkedin-status",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status2.json()["has_credentials"] is False


@pytest.mark.asyncio
async def test_delete_linkedin_clears_last_scraped(monkeypatch: pytest.MonkeyPatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "ENCRYPTION_KEY", key)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        token, _ = await _setup_user_with_profile(client)
        payload = jwt.decode(token, options={"verify_signature": False})
        uid = uuid.UUID(str(payload["sub"]))

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            profile.linkedin_email = "x@y.com"
            profile.linkedin_password_encrypted = "enc"
            profile.linkedin_last_scraped_at = datetime.now(timezone.utc)
            session.add(profile)
            await session.commit()
            break

        await client.delete(
            "/api/settings/linkedin-credentials",
            headers={"Authorization": f"Bearer {token}"},
        )

        async for session in _get_test_session():
            result = await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id == uid)
            )
            profile = result.scalar_one()
            assert profile.linkedin_last_scraped_at is None
            break


@pytest.mark.asyncio
async def test_settings_routes_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/settings/linkedin-status")
        assert r.status_code == 401
