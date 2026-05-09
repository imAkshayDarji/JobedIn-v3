import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request
from starlette.responses import Response

from app.middleware.error_handler import ErrorHandlerMiddleware
from slowapi.errors import RateLimitExceeded

from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import (
    _key_func,
    rate_limit_exceeded_handler,
    resolve_slowapi_storage_uri,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    method: str = "GET",
    path: str = "/test",
    headers: dict | None = None,
    state_user: object | None = None,
) -> Request:
    """Create a minimal Request with a Starlette scope dict."""
    raw_headers: list[tuple[bytes, bytes]] = []
    if headers:
        for k, v in headers.items():
            raw_headers.append((k.lower().encode(), v.encode()))

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": b"",
        "headers": raw_headers,
        "server": ("testserver", 80),
    }
    request = Request(scope)

    if state_user is not None:
        request.state.user = state_user

    return request


def _make_response(status_code: int = 200) -> Response:
    return Response(status_code=status_code, content=b"ok")


# ---------------------------------------------------------------------------
# ErrorHandlerMiddleware tests
# ---------------------------------------------------------------------------

@pytest.fixture
def error_middleware():
    dummy_app = MagicMock()
    return ErrorHandlerMiddleware(dummy_app)


async def test_error_handler_passes_through_on_success(error_middleware):
    request = _make_request()
    expected_response = _make_response(200)
    call_next = AsyncMock(return_value=expected_response)

    response = await error_middleware.dispatch(request, call_next)

    assert response.status_code == 200


async def test_error_handler_validation_error_returns_422(error_middleware):
    request = _make_request()

    validation_errors = [
        {"loc": ("body", "email"), "msg": "field required", "type": "value_error.missing"}
    ]
    exc = RequestValidationError(validation_errors)
    call_next = AsyncMock(side_effect=exc)

    response = await error_middleware.dispatch(request, call_next)

    assert response.status_code == 422
    body = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
    assert "VALIDATION_ERROR" in body
    assert "field required" in body


async def test_error_handler_unexpected_error_returns_500(error_middleware):
    request = _make_request()
    exc = RuntimeError("something broke")
    call_next = AsyncMock(side_effect=exc)

    with patch("app.middleware.error_handler.sentry_sdk") as mock_sentry:
        response = await error_middleware.dispatch(request, call_next)

    assert response.status_code == 500
    body = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
    assert "INTERNAL_ERROR" in body
    mock_sentry.capture_exception.assert_called_once_with(exc)


async def test_error_handler_includes_request_id(error_middleware):
    request = _make_request()
    exc = RuntimeError("fail")
    call_next = AsyncMock(side_effect=exc)

    with patch("app.middleware.error_handler.sentry_sdk"):
        response = await error_middleware.dispatch(request, call_next)

    body = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
    assert "request_id" in body


async def test_error_handler_sentry_breadcrumb_and_context(error_middleware):
    request = _make_request()
    exc = RuntimeError("unexpected")
    call_next = AsyncMock(side_effect=exc)

    with patch("app.middleware.error_handler.sentry_sdk") as mock_sentry:
        response = await error_middleware.dispatch(request, call_next)

    mock_sentry.add_breadcrumb.assert_called_once()
    mock_sentry.set_context.assert_called_once_with(
        "request",
        {"method": "GET", "path": "/test", "query": ""},
    )


def test_resolve_slowapi_storage_uri_blank():
    assert resolve_slowapi_storage_uri("") == "memory://"
    assert resolve_slowapi_storage_uri("   ") == "memory://"
    assert resolve_slowapi_storage_uri("\t\n") == "memory://"


def test_resolve_slowapi_storage_uri_redis():
    assert resolve_slowapi_storage_uri("redis://localhost:6379/0") == "redis://localhost:6379/0"
    assert resolve_slowapi_storage_uri("  redis://x  ") == "redis://x"


def test_resolve_slowapi_storage_uri_rediss():
    assert resolve_slowapi_storage_uri("rediss://user:pass@host:6379/0") == "rediss://user:pass@host:6379/0"


def test_resolve_slowapi_storage_uri_invalid_scheme():
    assert resolve_slowapi_storage_uri("\\t") == "memory://"
    assert resolve_slowapi_storage_uri("postgres://localhost/db") == "memory://"


# ---------------------------------------------------------------------------
# Rate Limit _key_func tests
# ---------------------------------------------------------------------------

def test_rate_limit_key_func_with_user():
    mock_user = MagicMock()
    mock_user.id = 42
    request = _make_request(state_user=mock_user)

    result = _key_func(request)

    assert result == "42"


def test_rate_limit_key_func_with_forwarded_for():
    request = _make_request(headers={"X-Forwarded-For": "203.0.113.50, 70.41.3.18"})
    # Ensure no user on state
    assert not hasattr(request.state, "user") or getattr(request.state, "user", None) is None

    result = _key_func(request)

    assert result == "203.0.113.50"


def test_rate_limit_key_func_fallback_to_remote_address():
    request = _make_request()

    with patch("app.middleware.rate_limit.get_remote_address", return_value="127.0.0.1"):
        result = _key_func(request)

    assert result == "127.0.0.1"


# ---------------------------------------------------------------------------
# Rate Limit exceeded handler test
# ---------------------------------------------------------------------------

async def test_rate_limit_exceeded_handler_returns_429():
    request = _make_request()
    mock_limit = MagicMock()
    mock_limit.error_message = None
    mock_limit.limit = "2 per 1 minute"
    exc = RateLimitExceeded(mock_limit)

    response = await rate_limit_exceeded_handler(request, exc)

    assert response.status_code == 429
    body = response.body.decode() if isinstance(response.body, bytes) else str(response.body)
    assert "RATE_LIMITED" in body
    assert response.headers.get("Retry-After") == "60"


# ---------------------------------------------------------------------------
# SecurityHeadersMiddleware tests
# ---------------------------------------------------------------------------

async def test_security_headers_middleware_adds_headers():
    from app.main import SecurityHeadersMiddleware

    dummy_app = MagicMock()
    middleware = SecurityHeadersMiddleware(dummy_app)

    request = _make_request()

    mock_response = MagicMock()
    mock_response.headers = {}

    call_next = AsyncMock(return_value=mock_response)

    response = await middleware.dispatch(request, call_next)

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["X-XSS-Protection"] == "0"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
