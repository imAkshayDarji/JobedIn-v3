from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.auth import router as auth_router
from app.routes.cover_letters import router as cover_letter_router
from app.routes.health import router as health_router
from app.routes.onboarding import router as onboarding_router
from app.routes.profile import router as profile_router
from app.routes.resumes import router as resume_router

if settings.SENTRY_DSN_BACKEND:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN_BACKEND,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(onboarding_router)
app.include_router(profile_router)
app.include_router(resume_router)
app.include_router(cover_letter_router)
