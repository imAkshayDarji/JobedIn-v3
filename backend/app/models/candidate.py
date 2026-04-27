import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, JSON as SA_JSON
from sqlmodel import Field, Relationship

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
    linkedin_last_scraped_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    onboarding_step: int = Field(default=0)
    onboarding_completed: bool = Field(default=False)

    skills: list["Skill"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    education: list["Education"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    experience: list["Experience"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    projects: list["Project"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    target_roles: list["TargetRole"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    certifications: list["Certification"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )
    languages: list["Language"] = Relationship(  # type: ignore[assignment]
        back_populates="candidate",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

