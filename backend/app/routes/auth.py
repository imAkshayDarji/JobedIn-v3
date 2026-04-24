import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.candidate import CandidateProfile

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
async def get_me(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "role": user.role,
    }


@router.get("/verify")
async def verify_token(user: CurrentUser = Depends(get_current_user)) -> dict:
    return {
        "valid": True,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        },
    }


@router.post("/sync-profile")
async def sync_profile(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    existing = result.scalar_one_or_none()

    if existing is None:
        profile = CandidateProfile(
            user_id=user.id,
            first_name="",
            last_name="",
        )
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
        return {
            "status": "created",
            "profile_id": str(profile.id),
        }

    return {
        "status": "exists",
        "profile_id": str(existing.id),
    }
