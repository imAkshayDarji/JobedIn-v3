import logging
import uuid
from typing import Union

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import CurrentUser, get_current_user
from app.database import get_async_session
from app.models.candidate import CandidateProfile
from app.models.certification import Certification
from app.models.education import Education
from app.models.experience import Experience
from app.models.language import Language
from app.models.project import Project
from app.models.skill import Skill
from app.models.target_role import TargetRole
from app.schemas.profile import (
    CertificationCreate,
    CertificationResponse,
    CertificationUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    LanguageCreate,
    LanguageResponse,
    LanguageUpdate,
    ProfileDetailResponse,
    ProfileMeResponse,
    ProfileUpdateRequest,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SkillCreate,
    SkillResponse,
    SkillUpdate,
    TargetRoleCreate,
    TargetRoleResponse,
    TargetRoleUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["profile"])

ENTITY_MODELS: dict[str, type] = {
    "educations": Education,
    "experiences": Experience,
    "skills": Skill,
    "projects": Project,
    "target-roles": TargetRole,
    "certifications": Certification,
    "languages": Language,
}


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


async def _get_owned_item(
    session: AsyncSession,
    model: type,
    item_id: uuid.UUID,
    candidate_id: uuid.UUID,
):
    result = await session.execute(
        select(model).where(
            model.id == item_id,
            model.candidate_id == candidate_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found.",
        )
    return item


# --- Profile endpoints ---


@router.get("/me", response_model=ProfileMeResponse)
async def get_profile_me(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProfileMeResponse:
    profile = await _resolve_profile(user.id, session)
    return ProfileMeResponse(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        onboarding_completed=profile.onboarding_completed,
        experience_level=profile.experience_level,
    )


@router.get("/full", response_model=ProfileDetailResponse)
async def get_profile_full(
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProfileDetailResponse:
    result = await session.execute(
        select(CandidateProfile)
        .where(CandidateProfile.user_id == user.id)
        .options(
            selectinload(CandidateProfile.education),
            selectinload(CandidateProfile.experience),
            selectinload(CandidateProfile.skills),
            selectinload(CandidateProfile.projects),
            selectinload(CandidateProfile.target_roles),
            selectinload(CandidateProfile.certifications),
            selectinload(CandidateProfile.languages),
        )
    )
    profile = result.unique().scalar_one_or_none()
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complete your profile first.",
        )

    return ProfileDetailResponse(
        id=profile.id,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
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
        onboarding_completed=profile.onboarding_completed,
        education=[
            EducationResponse(
                id=e.id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                institution=e.institution,
                degree=e.degree,
                field_of_study=e.field_of_study,
                start_date=e.start_date,
                end_date=e.end_date,
                grade=e.grade,
                description=e.description,
            )
            for e in profile.education
        ],
        experience=[
            ExperienceResponse(
                id=e.id,
                created_at=e.created_at,
                updated_at=e.updated_at,
                company=e.company,
                title=e.title,
                location=e.location,
                start_date=e.start_date,
                end_date=e.end_date,
                description=e.description,
                is_current=e.is_current,
            )
            for e in profile.experience
        ],
        skills=[
            SkillResponse(
                id=s.id,
                created_at=s.created_at,
                updated_at=s.updated_at,
                name=s.name,
                category=s.category,
                proficiency=s.proficiency,
            )
            for s in profile.skills
        ],
        projects=[
            ProjectResponse(
                id=p.id,
                created_at=p.created_at,
                updated_at=p.updated_at,
                name=p.name,
                description=p.description,
                url=p.url,
                start_date=p.start_date,
                end_date=p.end_date,
                technologies=p.technologies,
            )
            for p in profile.projects
        ],
        target_roles=[
            TargetRoleResponse(
                id=t.id,
                created_at=t.created_at,
                updated_at=t.updated_at,
                title=t.title,
                priority=t.priority,
                keywords=t.keywords,
            )
            for t in profile.target_roles
        ],
        certifications=[
            CertificationResponse(
                id=c.id,
                created_at=c.created_at,
                updated_at=c.updated_at,
                name=c.name,
                issuer=c.issuer,
                issue_date=c.issue_date,
                expiry_date=c.expiry_date,
                credential_url=c.credential_url,
            )
            for c in profile.certifications
        ],
        languages=[
            LanguageResponse(
                id=l.id,
                created_at=l.created_at,
                updated_at=l.updated_at,
                name=l.name,
                proficiency=l.proficiency,
            )
            for l in profile.languages
        ],
    )


@router.patch("/me", response_model=ProfileMeResponse)
async def patch_profile_me(
    request: ProfileUpdateRequest,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProfileMeResponse:
    profile = await _resolve_profile(user.id, session)

    update_data = request.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields to update.",
        )

    for field, value in update_data.items():
        setattr(profile, field, value)

    session.add(profile)
    await session.commit()
    await session.refresh(profile)

    return ProfileMeResponse(
        id=profile.id,
        first_name=profile.first_name,
        last_name=profile.last_name,
        onboarding_completed=profile.onboarding_completed,
        experience_level=profile.experience_level,
    )


# --- Education CRUD ---


@router.post("/educations", response_model=EducationResponse, status_code=status.HTTP_201_CREATED)
async def create_education(
    request: EducationCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> EducationResponse:
    profile = await _resolve_profile(user.id, session)
    item = Education(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return EducationResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        institution=item.institution,
        degree=item.degree,
        field_of_study=item.field_of_study,
        start_date=item.start_date,
        end_date=item.end_date,
        grade=item.grade,
        description=item.description,
    )


@router.put("/educations/{item_id}", response_model=EducationResponse)
async def update_education(
    item_id: uuid.UUID,
    request: EducationUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> EducationResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Education, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return EducationResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        institution=item.institution,
        degree=item.degree,
        field_of_study=item.field_of_study,
        start_date=item.start_date,
        end_date=item.end_date,
        grade=item.grade,
        description=item.description,
    )


@router.delete("/educations/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_education(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Education, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Experience CRUD ---


@router.post("/experiences", response_model=ExperienceResponse, status_code=status.HTTP_201_CREATED)
async def create_experience(
    request: ExperienceCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ExperienceResponse:
    profile = await _resolve_profile(user.id, session)
    item = Experience(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ExperienceResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company=item.company,
        title=item.title,
        location=item.location,
        start_date=item.start_date,
        end_date=item.end_date,
        description=item.description,
        is_current=item.is_current,
    )


@router.put("/experiences/{item_id}", response_model=ExperienceResponse)
async def update_experience(
    item_id: uuid.UUID,
    request: ExperienceUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ExperienceResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Experience, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ExperienceResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        company=item.company,
        title=item.title,
        location=item.location,
        start_date=item.start_date,
        end_date=item.end_date,
        description=item.description,
        is_current=item.is_current,
    )


@router.delete("/experiences/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_experience(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Experience, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Skill CRUD ---


@router.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    request: SkillCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SkillResponse:
    profile = await _resolve_profile(user.id, session)
    item = Skill(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return SkillResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        category=item.category,
        proficiency=item.proficiency,
    )


@router.put("/skills/{item_id}", response_model=SkillResponse)
async def update_skill(
    item_id: uuid.UUID,
    request: SkillUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SkillResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Skill, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return SkillResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        category=item.category,
        proficiency=item.proficiency,
    )


@router.delete("/skills/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Skill, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Project CRUD ---


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectResponse:
    profile = await _resolve_profile(user.id, session)
    item = Project(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ProjectResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        description=item.description,
        url=item.url,
        start_date=item.start_date,
        end_date=item.end_date,
        technologies=item.technologies,
    )


@router.put("/projects/{item_id}", response_model=ProjectResponse)
async def update_project(
    item_id: uuid.UUID,
    request: ProjectUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ProjectResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Project, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ProjectResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        description=item.description,
        url=item.url,
        start_date=item.start_date,
        end_date=item.end_date,
        technologies=item.technologies,
    )


@router.delete("/projects/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Project, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Target Role CRUD ---


@router.post("/target-roles", response_model=TargetRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_target_role(
    request: TargetRoleCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> TargetRoleResponse:
    profile = await _resolve_profile(user.id, session)
    item = TargetRole(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return TargetRoleResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        title=item.title,
        priority=item.priority,
        keywords=item.keywords,
    )


@router.put("/target-roles/{item_id}", response_model=TargetRoleResponse)
async def update_target_role(
    item_id: uuid.UUID,
    request: TargetRoleUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> TargetRoleResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, TargetRole, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return TargetRoleResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        title=item.title,
        priority=item.priority,
        keywords=item.keywords,
    )


@router.delete("/target-roles/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_target_role(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, TargetRole, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Certification CRUD ---


@router.post("/certifications", response_model=CertificationResponse, status_code=status.HTTP_201_CREATED)
async def create_certification(
    request: CertificationCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CertificationResponse:
    profile = await _resolve_profile(user.id, session)
    item = Certification(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return CertificationResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        issuer=item.issuer,
        issue_date=item.issue_date,
        expiry_date=item.expiry_date,
        credential_url=item.credential_url,
    )


@router.put("/certifications/{item_id}", response_model=CertificationResponse)
async def update_certification(
    item_id: uuid.UUID,
    request: CertificationUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> CertificationResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Certification, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return CertificationResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        issuer=item.issuer,
        issue_date=item.issue_date,
        expiry_date=item.expiry_date,
        credential_url=item.credential_url,
    )


@router.delete("/certifications/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_certification(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Certification, item_id, profile.id)
    await session.delete(item)
    await session.commit()


# --- Language CRUD ---


@router.post("/languages", response_model=LanguageResponse, status_code=status.HTTP_201_CREATED)
async def create_language(
    request: LanguageCreate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> LanguageResponse:
    profile = await _resolve_profile(user.id, session)
    item = Language(candidate_id=profile.id, **request.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return LanguageResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        proficiency=item.proficiency,
    )


@router.put("/languages/{item_id}", response_model=LanguageResponse)
async def update_language(
    item_id: uuid.UUID,
    request: LanguageUpdate,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> LanguageResponse:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Language, item_id, profile.id)

    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    session.add(item)
    await session.commit()
    await session.refresh(item)
    return LanguageResponse(
        id=item.id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        name=item.name,
        proficiency=item.proficiency,
    )


@router.delete("/languages/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_language(
    item_id: uuid.UUID,
    user: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    profile = await _resolve_profile(user.id, session)
    item = await _get_owned_item(session, Language, item_id, profile.id)
    await session.delete(item)
    await session.commit()
