import io
import uuid

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
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])


async def _get_profile(
    user_id: uuid.UUID, session: AsyncSession
) -> CandidateProfile:
    result = await session.execute(
        select(CandidateProfile).where(CandidateProfile.user_id == user_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate profile not found. Call /api/auth/sync-profile first.",
        )
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

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse PDF: {exc}",
        ) from exc

    return {
        "extracted_text": extracted_text,
        "page_count": len(reader.pages),
        "pre_fill": {
            "personal_info": None,
            "target_roles": [],
            "skills": [],
            "education": [],
            "experience": [],
        },
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
                start_date=edu_data.start_date,
                end_date=edu_data.end_date,
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
                start_date=exp_data.start_date,
                end_date=exp_data.end_date,
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
                start_date=e.start_date,
                end_date=e.end_date,
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
                start_date=ex.start_date,
                end_date=ex.end_date,
                description=ex.description,
                is_current=ex.is_current,
            )
            for ex in experience
        ],
    )
