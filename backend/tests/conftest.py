import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app

TEST_USER_ID = "user_test_" + str(uuid.uuid4())[:8]
TEST_EMAIL = "test@example.com"
TEST_JWT_SECRET = "test-jwt-secret-for-testing-only-min-32-chars!!"


def mint_jwt(
    user_id: str | None = None,
    email: str = TEST_EMAIL,
    expired: bool = False,
) -> str:
    uid = user_id or TEST_USER_ID
    now = datetime.now(timezone.utc)
    if expired:
        issued_at = now - timedelta(hours=2)
        expiry = now - timedelta(hours=1)
    else:
        issued_at = now
        expiry = now + timedelta(hours=1)

    payload = {
        "sub": uid,
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
    from app.middleware.rate_limit import limiter

    with patch.object(settings, "CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json"), \
         patch.object(settings, "RATE_LIMIT_ENABLED", False), \
         patch("app.auth._fetch_jwks", new_callable=AsyncMock, return_value={"test-kid": {}}), \
         patch("app.auth._decode_token", side_effect=_mock_decode_token):
        limiter.enabled = False
        yield
        limiter.enabled = settings.RATE_LIMIT_ENABLED


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = mint_jwt()
    return {"Authorization": f"Bearer {token}"}
