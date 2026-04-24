import uuid

from sqlalchemy import Column, JSON as SA_JSON
from sqlmodel import Field

from app.models.base import TimestampModel


class Resume(TimestampModel, table=True):
    __tablename__ = "resumes"

    user_id: uuid.UUID = Field(index=True)
    job_id: uuid.UUID | None = Field(default=None, foreign_key="jobs.id", ondelete="SET NULL")
    content_json: dict | None = Field(default=None, sa_column=Column(SA_JSON))
    ats_score: float | None = Field(default=None)
    ats_breakdown: dict | None = Field(default=None, sa_column=Column(SA_JSON))
    template_id: str | None = Field(default=None)
