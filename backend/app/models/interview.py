import uuid
from datetime import datetime

from sqlalchemy import Column, JSON as SA_JSON
from sqlmodel import Field

from app.models.base import TimestampModel


class InterviewPrep(TimestampModel, table=True):
    __tablename__ = "interview_preps"

    user_id: uuid.UUID = Field(index=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    questions: list | None = Field(default=None, sa_column=Column(SA_JSON))


class InterviewSession(TimestampModel, table=True):
    __tablename__ = "interview_sessions"

    user_id: uuid.UUID = Field(index=True)
    interview_prep_id: uuid.UUID = Field(
        foreign_key="interview_preps.id", ondelete="CASCADE"
    )
    messages: list | None = Field(default=None, sa_column=Column(SA_JSON))
    current_difficulty: int = Field(default=1)
    completed_at: datetime | None = Field(default=None)
