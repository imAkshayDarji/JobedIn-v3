import uuid

import jwt
import sentry_sdk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import SQLModel

from app.config import settings


class CurrentUser(SQLModel):
    id: uuid.UUID
    email: str
    role: str = "authenticated"


security_scheme = HTTPBearer(auto_error=False)


def _decode_token(token: str) -> dict:
    if not settings.SUPABASE_JWT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="SUPABASE_JWT_SECRET is not configured",
        )

    try:
        payload = jwt.decode(
            token,
            settings.SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    expected_issuer = f"{settings.SUPABASE_URL}/auth/v1"
    if settings.SUPABASE_URL and payload.get("iss") != expected_issuer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token issuer",
        )

    return payload


def _payload_to_user(payload: dict) -> CurrentUser:
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    email = payload.get("email", "")

    sentry_sdk.set_user({"id": str(user_id), "email": email})

    return CurrentUser(id=user_id, email=email, role=payload.get("role", "authenticated"))


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = _decode_token(credentials.credentials)
    return _payload_to_user(payload)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> CurrentUser | None:
    if credentials is None:
        return None

    try:
        payload = _decode_token(credentials.credentials)
        return _payload_to_user(payload)
    except HTTPException:
        return None
