import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_async_session
from app.main import app

TEST_JWT_SECRET = "test-jwt-secret-for-testing-only-min-32-chars!!"
TEST_SUPABASE_URL = "https://test.supabase.co"


def mint_jwt(
    user_id: str | None = None,
    email: str = "test@example.com",
    expired: bool = False,
    secret: str = TEST_JWT_SECRET,
    issuer: str | None = None,
) -> str:
    uid = user_id or str(uuid.uuid4())
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


@pytest.fixture
def auth_headers() -> dict[str, str]:
    token = mint_jwt()
    return {"Authorization": f"Bearer {token}"}
