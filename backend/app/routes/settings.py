import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.candidate import CandidateProfile
from app.schemas.settings import LinkedInCredentialsRequest, LinkedInStatusResponse
from app.services.credential_crypto import encrypt_value

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


async def _resolve_profile(
    user_id: str, session: AsyncSession
) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )
    return profile


@router.post("/linkedin-credentials", status_code=status.HTTP_200_OK)
async def save_linkedin_credentials(
    request: LinkedInCredentialsRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    profile = await _resolve_profile(user.id, session)

    try:
        encrypted_password = encrypt_value(request.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )

    profile.linkedin_email = request.email
    profile.linkedin_password_encrypted = encrypted_password
    session.add(profile)
    await session.commit()

    logger.info(
        "linkedin_credentials_saved",
        extra={"user_id": str(user.id)},
    )

    return {"message": "LinkedIn credentials saved successfully"}


@router.get("/linkedin-status", response_model=LinkedInStatusResponse)
async def get_linkedin_status(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> LinkedInStatusResponse:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user.id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        return LinkedInStatusResponse(has_credentials=False)

    has_creds = bool(profile.linkedin_email and profile.linkedin_password_encrypted)
    last_scraped = profile.linkedin_last_scraped_at.isoformat() if profile.linkedin_last_scraped_at else None

    return LinkedInStatusResponse(
        has_credentials=has_creds,
        email=profile.linkedin_email if has_creds else None,
        last_scraped_at=last_scraped,
    )


@router.delete("/linkedin-credentials", status_code=status.HTTP_200_OK)
async def delete_linkedin_credentials(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    profile = await _resolve_profile(user.id, session)

    profile.linkedin_email = None
    profile.linkedin_password_encrypted = None
    profile.linkedin_last_scraped_at = None
    session.add(profile)
    await session.commit()

    logger.info(
        "linkedin_credentials_deleted",
        extra={"user_id": str(user.id)},
    )

    return {"message": "LinkedIn credentials deleted successfully"}
