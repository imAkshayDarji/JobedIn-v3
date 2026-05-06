import uuid
from datetime import datetime

from sqlalchemy import Column, Index, JSON as SA_JSON, text
from sqlmodel import Field

from app.models.base import TimestampModel


class InterviewPrep(TimestampModel, table=True):
    __tablename__ = "interview_preps"
    __table_args__ = (
        Index("ix_interview_preps_user_created", "user_id", text("created_at DESC")),
    )

    user_id: str = Field(index=True)
    job_id: uuid.UUID | None = Field(default=None, foreign_key="jobs.id", ondelete="SET NULL")
    questions: list | None = Field(default=None, sa_column=Column(SA_JSON))
    status: str = Field(default="generating")
    job_description: str | None = Field(default=None)
    job_title: str | None = Field(default=None)
    company_name: str | None = Field(default=None)


class InterviewSession(TimestampModel, table=True):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        Index("ix_interview_sessions_user_created", "user_id", text("created_at DESC")),
    )

    user_id: str = Field(index=True)
    interview_prep_id: uuid.UUID = Field(
        foreign_key="interview_preps.id", ondelete="CASCADE"
    )
    messages: list | None = Field(default=None, sa_column=Column(SA_JSON))
    current_difficulty: int = Field(default=1)
    status: str = Field(default="active")
    overall_score: float | None = Field(default=None)
    questions_answered: int = Field(default=0)
    completed_at: datetime | None = Field(default=None)
