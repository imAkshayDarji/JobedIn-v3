from datetime import datetime

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import ExperienceLevel, JobSource, RemotePolicy, TimestampModel


class Job(TimestampModel, table=True):
    __tablename__ = "jobs"
    __table_args__ = (
        UniqueConstraint(
            "source",
            "external_id",
            name="uq_jobs_source_external_id",
        ),
        Index("ix_jobs_title", "title"),
        Index("ix_jobs_company", "company"),
        Index("ix_jobs_location", "location"),
    )

    source: JobSource
    source_url: str | None = Field(default=None)
    external_id: str | None = Field(default=None, index=True)
    title: str
    company: str
    description: str | None = Field(default=None)
    salary_min: int | None = Field(default=None)
    salary_max: int | None = Field(default=None)
    salary_currency: str = Field(default="USD")
    location: str | None = Field(default=None)
    experience_level: ExperienceLevel | None = Field(default=None)
    job_type: str | None = Field(default=None)
    remote_policy: RemotePolicy | None = Field(default=None)
    ats_platform: str | None = Field(default=None)
    apply_url: str | None = Field(default=None)
    scraped_at: datetime | None = Field(default=None)
    alternate_sources: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
