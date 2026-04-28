import uuid
from datetime import datetime

from sqlalchemy import Column, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import TimestampModel


class JobMatch(TimestampModel, table=True):
    __tablename__ = "job_matches"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "job_id",
            name="uq_job_matches_user_job",
        ),
        Index("ix_job_matches_user_score", "user_id", "match_score"),
    )

    user_id: uuid.UUID = Field(index=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    match_score: float
    skills_score: float
    experience_score: float
    role_relevance_score: float
    location_score: float
    matched_skills: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    missing_skills: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    scored_at: datetime
