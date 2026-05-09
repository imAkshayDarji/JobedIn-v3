import logging
from urllib.parse import urlparse

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.config import settings
from app.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


def resolve_slowapi_storage_uri(redis_url: str) -> str:
    """
    Return a limits.storage URI SlowAPI can construct.

    Invalid or blank REDIS_URL must not reach SlowAPI as None (SlowAPI then reads
    RATELIMIT_STORAGE_URL from .env, which can crash import) nor as a bogus scheme.
    """
    candidate = redis_url.strip()
    if not candidate:
        logger.warning(
            "REDIS_URL is unset or whitespace-only; rate limits use in-memory storage "
            "(fine for one instance; set redis:// or rediss:// for Redis-backed limits)."
        )
        return "memory://"
    scheme = urlparse(candidate).scheme.lower()
    if scheme in ("redis", "rediss"):
        return candidate
    logger.warning(
        "REDIS_URL is not redis:// or rediss:// (scheme=%r); rate limits use in-memory storage.",
        scheme or "(empty)",
    )
    return "memory://"


def _key_func(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return str(user.id)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


_limiter_storage_uri = resolve_slowapi_storage_uri(settings.REDIS_URL)

limiter = Limiter(
    key_func=_key_func,
    enabled=settings.RATE_LIMIT_ENABLED,
    default_limits=[settings.RATE_LIMIT_DEFAULT],
    storage_uri=_limiter_storage_uri,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    error_response = ErrorResponse(
        error=ErrorDetail(
            code="RATE_LIMITED",
            message="Too many requests. Please slow down and try again later.",
        ),
    )
    return JSONResponse(
        status_code=429,
        content=error_response.model_dump(exclude_none=True),
        headers={"Retry-After": "60"},
    )
