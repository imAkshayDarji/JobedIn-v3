import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.candidate import CandidateProfile
from app.schemas.resume import ProfileMeResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])


@router.get("/me", response_model=ProfileMeResponse)
async def get_profile_me(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProfileMeResponse:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )

    return ProfileMeResponse(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        onboarding_completed=profile.onboarding_completed,
        experience_level=profile.experience_level,
    )
