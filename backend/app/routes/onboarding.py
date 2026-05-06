import io
import logging
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.candidate import CandidateProfile
from app.models.education import Education
from app.models.experience import Experience
from app.models.skill import Skill
from app.models.target_role import TargetRole
from app.schemas.onboarding import (
    OnboardingPersonalInfo,
    OnboardingSaveRequest,
    OnboardingSaveResponse,
    OnboardingStatusResponse,
    ParsedResume,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

logger = logging.getLogger(__name__)


def _ym_to_date(value: str | None) -> date | None:
    if not value:
        return None
    parts = value.split("-")
    return date(int(parts[0]), int(parts[1]), 1)


def _date_to_ym(value: date | None) -> str | None:
    if not value:
        return None
    return value.strftime("%Y-%m")


async def _get_profile(
    user_id: str, session: AsyncSession
) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        profile = CandidateProfile(user_id=user_id, first_name="", last_name="")
        session.add(profile)
        await session.commit()
        await session.refresh(profile)
    return profile


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> dict:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only PDF files are accepted",
        )

    from app.config import settings as app_settings

    max_bytes = app_settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File too large. Maximum size is {app_settings.MAX_UPLOAD_SIZE_MB}MB.",
        )

    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        extracted_text = "\n".join(text_parts)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse PDF. Please ensure the file is a valid PDF document.",
        )

    return {
        "extracted_text": extracted_text,
        "page_count": len(reader.pages),
        "pre_fill": await _parse_resume_with_ai(extracted_text),
    }


async def _parse_resume_with_ai(resume_text: str) -> dict:
    if not resume_text.strip():
        return _empty_pre_fill()

    try:
        from app.services.ai_client import AIClient
        from app.services.ai_prompts import parse_resume_prompt

        client = AIClient()
        result = await client.call(
            task="parse_resume",
            messages=parse_resume_prompt(resume_text),
            response_model=ParsedResume,
            context={"pipeline_step": "parse_resume"},
        )
        parsed: ParsedResume = result.content

        personal_info = None
        pi = parsed.personal_info
        if pi and (pi.first_name or pi.last_name):
            personal_info = {
                "first_name": pi.first_name or "",
                "last_name": pi.last_name or "",
                "headline": pi.headline,
                "summary": pi.summary,
                "location": pi.location,
                "phone": pi.phone,
                "experience_level": pi.experience_level,
                "linkedin_url": pi.linkedin_url,
                "github_url": pi.github_url,
                "portfolio_url": pi.portfolio_url,
                "website_url": pi.website_url,
            }

        return {
            "personal_info": personal_info,
            "target_roles": [r.model_dump() for r in parsed.target_roles],
            "skills": [s.model_dump() for s in parsed.skills],
            "education": [e.model_dump() for e in parsed.education],
            "experience": [x.model_dump() for x in parsed.experience],
        }
    except Exception:
        logger.warning("AI resume parsing failed, returning empty pre_fill", exc_info=True)
        return _empty_pre_fill()


def _empty_pre_fill() -> dict:
    return {
        "personal_info": None,
        "target_roles": [],
        "skills": [],
        "education": [],
        "experience": [],
    }


@router.post("/save", response_model=OnboardingSaveResponse)
async def save_onboarding(
    request: OnboardingSaveRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OnboardingSaveResponse:
    profile = await _get_profile(user.id, session)

    try:
        pi = request.personal_info
        profile.first_name = pi.first_name
        profile.last_name = pi.last_name
        profile.headline = pi.headline
        profile.summary = pi.summary
        profile.location = pi.location
        profile.phone = pi.phone
        profile.linkedin_url = pi.linkedin_url
        profile.github_url = pi.github_url
        profile.portfolio_url = pi.portfolio_url
        profile.website_url = pi.website_url
        if pi.experience_level:
            profile.experience_level = pi.experience_level
        profile.onboarding_step = 5
        profile.onboarding_completed = True
        session.add(profile)

        await session.execute(
            delete(TargetRole).where(TargetRole.candidate_id == profile.id)
        )
        for role_data in request.target_roles:
            role = TargetRole(
                candidate_id=profile.id,
                title=role_data.title,
                priority=role_data.priority,
                keywords=role_data.keywords,
            )
            session.add(role)

        await session.execute(
            delete(Skill).where(Skill.candidate_id == profile.id)
        )
        for skill_data in request.skills:
            skill = Skill(
                candidate_id=profile.id,
                name=skill_data.name,
                category=skill_data.category,
                proficiency=skill_data.proficiency,
            )
            session.add(skill)

        await session.execute(
            delete(Education).where(Education.candidate_id == profile.id)
        )
        for edu_data in request.education:
            edu = Education(
                candidate_id=profile.id,
                institution=edu_data.institution,
                degree=edu_data.degree,
                field_of_study=edu_data.field_of_study,
                start_date=_ym_to_date(edu_data.start_date),
                end_date=_ym_to_date(edu_data.end_date),
                grade=edu_data.grade,
                description=edu_data.description,
            )
            session.add(edu)

        await session.execute(
            delete(Experience).where(Experience.candidate_id == profile.id)
        )
        for exp_data in request.experience:
            exp = Experience(
                candidate_id=profile.id,
                company=exp_data.company,
                title=exp_data.title,
                location=exp_data.location,
                start_date=_ym_to_date(exp_data.start_date),
                end_date=_ym_to_date(exp_data.end_date),
                description=exp_data.description,
                is_current=exp_data.is_current,
            )
            session.add(exp)

        await session.commit()
        await session.refresh(profile)

    except Exception:
        await session.rollback()
        raise

    return OnboardingSaveResponse(
        profile_id=profile.id,
        created_target_roles=len(request.target_roles),
        created_skills=len(request.skills),
        created_education=len(request.education),
        created_experience=len(request.experience),
    )


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> OnboardingStatusResponse:
    profile = await _get_profile(user.id, session)

    target_roles_result = await session.execute(
        select(TargetRole).where(TargetRole.candidate_id == profile.id)
    )
    target_roles = target_roles_result.scalars().all()

    skills_result = await session.execute(
        select(Skill).where(Skill.candidate_id == profile.id)
    )
    skills = skills_result.scalars().all()

    education_result = await session.execute(
        select(Education).where(Education.candidate_id == profile.id)
    )
    education = education_result.scalars().all()

    experience_result = await session.execute(
        select(Experience).where(Experience.candidate_id == profile.id)
    )
    experience = experience_result.scalars().all()

    completed_sections: list[str] = []
    if profile.first_name or profile.last_name:
        completed_sections.append("personal_info")
    if target_roles:
        completed_sections.append("target_roles")
    if skills:
        completed_sections.append("skills")
    if education:
        completed_sections.append("education")
    if experience:
        completed_sections.append("experience")

    section_count = len(completed_sections)
    completion_percentage = min(section_count * 20, 100)

    next_step = 1
    if profile.onboarding_completed:
        next_step = 6
    elif profile.onboarding_step > 0:
        next_step = profile.onboarding_step + 1

    personal_info: OnboardingPersonalInfo | None = None
    if profile.first_name or profile.last_name:
        personal_info = OnboardingPersonalInfo(
            first_name=profile.first_name,
            last_name=profile.last_name,
            headline=profile.headline,
            summary=profile.summary,
            location=profile.location,
            phone=profile.phone,
            experience_level=profile.experience_level,
            linkedin_url=profile.linkedin_url,
            github_url=profile.github_url,
            portfolio_url=profile.portfolio_url,
            website_url=profile.website_url,
        )

    from app.schemas.onboarding import (
        OnboardingEducation,
        OnboardingExperience,
        OnboardingSkill,
        OnboardingTargetRole,
    )

    return OnboardingStatusResponse(
        onboarding_step=profile.onboarding_step,
        onboarding_completed=profile.onboarding_completed,
        completion_percentage=completion_percentage,
        completed_sections=completed_sections,
        next_step=next_step,
        personal_info=personal_info,
        target_roles=[
            OnboardingTargetRole(
                title=tr.title, priority=tr.priority, keywords=tr.keywords
            )
            for tr in target_roles
        ],
        skills=[
            OnboardingSkill(
                name=s.name, category=s.category, proficiency=s.proficiency
            )
            for s in skills
        ],
        education=[
            OnboardingEducation(
                institution=e.institution,
                degree=e.degree,
                field_of_study=e.field_of_study,
                start_date=_date_to_ym(e.start_date),
                end_date=_date_to_ym(e.end_date),
                grade=e.grade,
                description=e.description,
            )
            for e in education
        ],
        experience=[
            OnboardingExperience(
                company=ex.company,
                title=ex.title,
                location=ex.location,
                start_date=_date_to_ym(ex.start_date),
                end_date=_date_to_ym(ex.end_date),
                description=ex.description,
                is_current=ex.is_current,
            )
            for ex in experience
        ],
    )
