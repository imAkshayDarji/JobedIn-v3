from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limit import limiter, rate_limit_exceeded_handler
from app.routes.applications import router as applications_router
from app.routes.apply import apply_router
from app.routes.auth import router as auth_router
from app.routes.cover_letters import router as cover_letter_router
from app.routes.dashboard import router as dashboard_router
from app.routes.health import router as health_router
from app.routes.interview import router as interview_router
from app.routes.jobs import router as jobs_router
from app.routes.onboarding import router as onboarding_router
from app.routes.profile import router as profile_router
from app.routes.resumes import router as resume_router
from app.routes.settings import router as settings_router
from app.schemas.errors import ErrorDetail, ErrorResponse


def _before_send(event, hint):
    if event.get("request"):
        headers = event["request"].get("headers", {})
        scrub_keys = {"authorization", "cookie", "set-cookie"}
        if isinstance(headers, dict):
            for key in scrub_keys:
                headers.pop(key, None)
        elif isinstance(headers, list):
            headers = [
                h for h in headers
                if not (isinstance(h, (list, tuple)) and len(h) == 2 and h[0].lower() in scrub_keys)
            ]
            event["request"]["headers"] = headers

    contexts = event.get("contexts", {})
    for ctx_name in ("app", "device", "os", "browser"):
        ctx = contexts.get(ctx_name, {})
        if isinstance(ctx, dict):
            for key in ("password", "token", "secret"):
                ctx.pop(key, None)

    return event


if settings.SENTRY_DSN_BACKEND:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN_BACKEND,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
        before_send=_before_send,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    from app.services.redis_pool import close_redis

    await close_redis()


app = FastAPI(
    title="JobedIn API",
    version="0.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

app.add_middleware(ErrorHandlerMiddleware)

cors_origins = [
    origin.strip()
    for origin in settings.CORS_ORIGINS.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        return response


app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import logging
    import uuid

    import sentry_sdk

    from app.schemas.errors import ErrorDetail, ErrorResponse

    logger = logging.getLogger(__name__)
    request_id = str(uuid.uuid4())

    logger.exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
        },
    )

    sentry_sdk.add_breadcrumb(
        category="request",
        message=f"{request.method} {request.url.path}",
        level="error",
    )
    sentry_sdk.set_context(
        "request",
        {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params),
        },
    )
    sentry_sdk.capture_exception(exc)

    error_response = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred. Please try again later.",
        ),
        request_id=request_id,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(exclude_none=True),
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(applications_router)
app.include_router(apply_router)
app.include_router(dashboard_router)
app.include_router(onboarding_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(cover_letter_router)
app.include_router(interview_router)
app.include_router(jobs_router)
app.include_router(settings_router)
