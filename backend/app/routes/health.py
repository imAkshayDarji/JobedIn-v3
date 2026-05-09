from fastapi import APIRouter

from app.middleware.rate_limit import limiter

router = APIRouter()


@router.get("/health")
@limiter.exempt
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
