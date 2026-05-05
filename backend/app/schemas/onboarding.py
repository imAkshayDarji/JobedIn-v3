from datetime import date
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


YearMonth = Annotated[
    str | None,
    Field(default=None, pattern=r"^\d{4}-\d{2}$"),
]


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
    start_date: YearMonth
    end_date: YearMonth
    grade: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def coerce_empty_string(cls, v: object) -> str | None:
        if v == "":
            return None
        return v


class OnboardingExperience(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    title: str = Field(min_length=1, max_length=200)
    location: str | None = Field(default=None, max_length=200)
    start_date: YearMonth
    end_date: YearMonth
    description: str | None = Field(default=None, max_length=2000)
    is_current: bool = Field(default=False)

    @field_validator("start_date", "end_date", mode="before")
    @classmethod
    def coerce_empty_string(cls, v: object) -> str | None:
        if v == "":
            return None
        return v


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


class ParsedPersonalInfo(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    headline: str | None = None
    summary: str | None = None
    location: str | None = None
    phone: str | None = None
    experience_level: str | None = None
    linkedin_url: str | None = None
    github_url: str | None = None
    portfolio_url: str | None = None
    website_url: str | None = None


class ParsedTargetRole(BaseModel):
    title: str
    priority: int = 0
    keywords: str | None = None


class ParsedSkill(BaseModel):
    name: str
    category: str | None = None
    proficiency: str | None = None


class ParsedEducation(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    grade: str | None = None
    description: str | None = None


class ParsedExperience(BaseModel):
    company: str | None = None
    title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    description: str | None = None
    is_current: bool = False


class ParsedResume(BaseModel):
    personal_info: ParsedPersonalInfo | None = None
    target_roles: list[ParsedTargetRole] = []
    skills: list[ParsedSkill] = []
    education: list[ParsedEducation] = []
    experience: list[ParsedExperience] = []


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
