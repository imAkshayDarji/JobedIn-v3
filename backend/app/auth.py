import logging
import time

import httpx
import jwt
import sentry_sdk
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import SQLModel

from app.config import settings

logger = logging.getLogger(__name__)


class CurrentUser(SQLModel):
    id: str
    email: str
    role: str = "authenticated"


security_scheme = HTTPBearer(auto_error=False)

_JWKS_CACHE: dict[str, dict] = {}
_JWKS_CACHE_EXPIRY: float = 0.0
_JWKS_CACHE_TTL: float = 3600.0


async def _fetch_jwks() -> dict[str, dict]:
    global _JWKS_CACHE, _JWKS_CACHE_EXPIRY

    if _JWKS_CACHE and time.time() < _JWKS_CACHE_EXPIRY:
        return _JWKS_CACHE

    jwks_url = settings.CLERK_JWKS_URL
    if not jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="CLERK_JWKS_URL is not configured",
        )

    async with httpx.AsyncClient() as client:
        response = await client.get(jwks_url)
        response.raise_for_status()

    jwks_data = response.json()
    keys: dict[str, dict] = {}
    for key in jwks_data.get("keys", []):
        kid = key.get("kid")
        if kid:
            keys[kid] = key

    _JWKS_CACHE = keys
    _JWKS_CACHE_EXPIRY = time.time() + _JWKS_CACHE_TTL

    return keys


def _decode_token(token: str, jwks: dict[str, dict]) -> dict:
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {type(e).__name__}",
        )

    kid = unverified_header.get("kid")
    if not kid or kid not in jwks:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token key ID not found in JWKS",
        )

    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwks[kid])

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning("JWT debug: invalid token - %s: %s", type(e).__name__, e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {type(e).__name__}",
        )

    return payload


def _payload_to_user(payload: dict) -> CurrentUser:
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
        )

    email = ""
    email_data = payload.get("email")
    if isinstance(email_data, str):
        email = email_data

    sentry_sdk.set_user({"id": user_id, "email": email})

    return CurrentUser(id=user_id, email=email, role="authenticated")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> CurrentUser:
    if settings.BYPASS_AUTH:
        logger.warning("Auth bypass active — returning dev user %s", settings.BYPASS_AUTH_USER_EMAIL)
        return CurrentUser(
            id=settings.BYPASS_AUTH_USER_ID,
            email=settings.BYPASS_AUTH_USER_EMAIL,
            role="authenticated",
        )

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwks = await _fetch_jwks()
    payload = _decode_token(credentials.credentials, jwks)
    return _payload_to_user(payload)


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
) -> CurrentUser | None:
    if settings.BYPASS_AUTH:
        return CurrentUser(
            id=settings.BYPASS_AUTH_USER_ID,
            email=settings.BYPASS_AUTH_USER_EMAIL,
            role="authenticated",
        )

    if credentials is None:
        return None

    try:
        jwks = await _fetch_jwks()
        payload = _decode_token(credentials.credentials, jwks)
        return _payload_to_user(payload)
    except HTTPException:
        return None
