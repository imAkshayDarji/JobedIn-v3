from datetime import date
from uuid import UUID

from pydantic import BaseModel, Field


class OnboardingTargetRole(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: int = Field(default=0, ge=0, le=10)
    keywords: str | None = Field(default=None, max_length=1000)


class OnboardingSkill(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=100)
    proficiency: str | None = Field(default=None, max_length=50)


class OnboardingEducation(BaseModel):
    institution: str = Field(min_length=1, max_length=200)
    degree: str = Field(min_length=1, max_length=200)
    field_of_study: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)


class OnboardingExperience(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    description: str | None = Field(default=None, max_length=2000)
    is_current: bool = Field(default=False)


class OnboardingPersonalInfo(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    headline: str | None = Field(default=None, max_length=200)
    summary: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=200)
    phone: str | None = Field(default=None, max_length=50)
    experience_level: str | None = Field(default=None)
    linkedin_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    portfolio_url: str | None = Field(default=None, max_length=500)
    website_url: str | None = Field(default=None, max_length=500)


class OnboardingSaveRequest(BaseModel):
    personal_info: OnboardingPersonalInfo
    target_roles: list[OnboardingTargetRole] = Field(default_factory=list)
    skills: list[OnboardingSkill] = Field(default_factory=list)
    education: list[OnboardingEducation] = Field(default_factory=list)
    experience: list[OnboardingExperience] = Field(default_factory=list)


class OnboardingSaveResponse(BaseModel):
    profile_id: UUID
    created_target_roles: int
    created_skills: int
    created_education: int
    created_experience: int


class OnboardingStatusResponse(BaseModel):
    onboarding_step: int
    onboarding_completed: bool
    completion_percentage: int
    completed_sections: list[str]
    next_step: int
    personal_info: OnboardingPersonalInfo | None
    target_roles: list[OnboardingTargetRole]
    skills: list[OnboardingSkill]
    education: list[OnboardingEducation]
    experience: list[OnboardingExperience]
