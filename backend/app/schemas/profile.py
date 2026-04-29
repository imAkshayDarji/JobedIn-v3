from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Personal Info ---


class ProfileUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    experience_level: str | None = Field(default=None)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)


class ProfileMeResponse(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    onboarding_completed: bool
    experience_level: str | None = None


# --- Education ---


class EducationCreate(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: str = Field(min_length=1, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)


class EducationUpdate(BaseModel):
    institution: str | None = Field(default=None, min_length=1, max_length=200)
    degree: str | None = Field(default=None, min_length=1, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)


class EducationResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    institution: str
    degree: str
    field_of_study: str | None
    start_date: date | None
    end_date: date | None
    grade: str | None
    description: str | None


# --- Experience ---


class ExperienceCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    description: str | None = Field(default=None, max_length=2000)
    is_current: bool = Field(default=False)


class ExperienceUpdate(BaseModel):
    company: str | None = Field(default=None, min_length=1, max_length=200)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    description: str | None = Field(default=None, max_length=2000)
    is_current: bool | None = Field(default=None)


class ExperienceResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    company: str
    title: str
    location: str | None
    start_date: date | None
    end_date: date | None
    description: str | None
    is_current: bool


# --- Skill ---


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class SkillResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    category: str | None
    proficiency: str | None


# --- Project ---


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    url: str | None = Field(default=None, max_length=500)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    technologies: str | None = Field(default=None, max_length=2000)


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    url: str | None = Field(default=None, max_length=500)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    technologies: str | None = Field(default=None, max_length=2000)


class ProjectResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    description: str | None
    url: str | None
    start_date: date | None
    end_date: date | None
    technologies: str | None


# --- Target Role ---


class TargetRoleCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=0, ge=0, le=10)
    keywords: str | None = Field(default=None, max_length=1000)


class TargetRoleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    priority: int | None = Field(default=None, ge=0, le=10)
    keywords: str | None = Field(default=None, max_length=1000)


class TargetRoleResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    title: str
    priority: int
    keywords: str | None


# --- Certification ---


class CertificationCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issue_date: date | None = Field(default=None)
    expiry_date: date | None = Field(default=None)
    credential_url: str | None = Field(default=None, max_length=500)


class CertificationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    issuer: str | None = Field(default=None, max_length=200)
    issue_date: date | None = Field(default=None)
    expiry_date: date | None = Field(default=None)
    credential_url: str | None = Field(default=None, max_length=500)


class CertificationResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    issuer: str | None
    issue_date: date | None
    expiry_date: date | None
    credential_url: str | None


# --- Language ---


class LanguageCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class LanguageUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class LanguageResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    name: str
    proficiency: str | None


# --- Full Profile Detail ---


class ProfileDetailResponse(BaseModel):
    id: UUID
    created_at: datetime
    updated_at: datetime
    first_name: str
    last_name: str
    headline: str | None
    summary: str | None
    location: str | None
    phone: str | None
    experience_level: str | None
    linkedin_url: str | None
    github_url: str | None
    portfolio_url: str | None
    website_url: str | None
    onboarding_completed: bool

    education: list[EducationResponse]
    experience: list[ExperienceResponse]
    skills: list[SkillResponse]
    projects: list[ProjectResponse]
    target_roles: list[TargetRoleResponse]
    certifications: list[CertificationResponse]
    languages: list[LanguageResponse]
