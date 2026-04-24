import uuid

from sqlmodel import Field, SQLModel

from app.models.base import ExperienceLevel, TimestampModel


class CandidateProfile(TimestampModel, table=True):
    __tablename__ = "candidate_profiles"

    user_id: uuid.UUID = Field(unique=True, index=True)
    first_name: str
    last_name: str
    headline: str | None = Field(default=None)
    summary: str | None = Field(default=None)
    location: str | None = Field(default=None)
    phone: str | None = Field(default=None)
    linkedin_url: str | None = Field(default=None)
    github_url: str | None = Field(default=None)
    portfolio_url: str | None = Field(default=None)
    website_url: str | None = Field(default=None)
    experience_level: ExperienceLevel | None = Field(default=None)
    linkedin_email: str | None = Field(default=None)
    linkedin_password_encrypted: str | None = Field(default=None)
    onboarding_step: int = Field(default=0)
    onboarding_completed: bool = Field(default=False)
