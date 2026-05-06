import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

TEST_USER_ID = "user_test_" + str(uuid.uuid4())[:8]
TEST_EMAIL = "test@example.com"
TEST_JWT_SECRET = "test-jwt-secret-for-testing-only-min-32-chars!!"


def _mint_jwt(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    expired: bool = False,
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
        "iss": "https://clerk.test",
        "iat": issued_at,
        "exp": expiry,
    }

    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


def _mock_decode_token(token: str, _jwks: dict) -> dict:
    return jwt.decode(
        token,
        TEST_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


@pytest.fixture(autouse=True)
def _set_test_settings():
    with patch.object(settings, "CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json"), \
         patch("app.auth._fetch_jwks", new_callable=AsyncMock, return_value={"test-kid": {}}), \
         patch("app.auth._decode_token", side_effect=_mock_decode_token):
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
    from app.auth import _fetch_jwks
    from fastapi import HTTPException

    expired_token = _mint_jwt(expired=True)

    def _decode_expired(token: str, jwks: dict) -> dict:
        raise HTTPException(status_code=401, detail="Token has expired")

    with patch("app.auth._decode_token", side_effect=_decode_expired):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/auth/me",
                headers={"Authorization": f"Bearer {expired_token}"},
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
    from app.auth import _fetch_jwks
    from fastapi import HTTPException

    def _decode_invalid(token: str, jwks: dict) -> dict:
        raise HTTPException(status_code=401, detail="Invalid token: DecodeError")

    with patch("app.auth._decode_token", side_effect=_decode_invalid):
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
