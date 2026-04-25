import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

TEST_JWT_SECRET = "test-jwt-secret-for-testing-only-min-32-chars!!"
TEST_SUPABASE_URL = "https://test.supabase.co"
TEST_USER_ID = str(uuid.uuid4())
TEST_EMAIL = "test@example.com"


def _mint_jwt(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    expired: bool = False,
    secret: str = TEST_JWT_SECRET,
    issuer: str | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    if expired:
        issued_at = now - timedelta(hours=2)
        expiry = now - timedelta(hours=1)
    else:
        issued_at = now
        expiry = now + timedelta(hours=1)

    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "iss": issuer or f"{TEST_SUPABASE_URL}/auth/v1",
        "iat": issued_at,
        "exp": expiry,
        "aud": "authenticated",
    }

    return jwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def _set_test_settings():
    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET), patch.object(
        settings, "SUPABASE_URL", TEST_SUPABASE_URL
    ):
        yield


@pytest.mark.asyncio
async def test_get_current_user_valid_token():
    token = _mint_jwt()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == TEST_EMAIL
    assert data["role"] == "authenticated"


@pytest.mark.asyncio
async def test_get_current_user_expired_token():
    token = _mint_jwt(expired=True)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert "expired" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_current_user_no_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer garbage-token-here"},
        )

    assert response.status_code == 401
    assert "invalid" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_auth_me_returns_user():
    token = _mint_jwt()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert "email" in data
    assert "role" in data
    assert data["email"] == TEST_EMAIL


@pytest.mark.asyncio
async def test_auth_me_unauthenticated():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/auth/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_verify_valid_token():
    token = _mint_jwt()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/verify",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True
    assert data["user"]["email"] == TEST_EMAIL


@pytest.mark.asyncio
async def test_health_check_still_works():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_invalid_issuer_rejected():
    token = _mint_jwt(issuer="https://evil.com/auth/v1")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert "issuer" in response.json()["detail"].lower()
