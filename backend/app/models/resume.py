import uuid

from sqlalchemy import Column, Index, JSON as SA_JSON, text
from sqlmodel import Field

from app.models.base import TimestampModel


class Resume(TimestampModel, table=True):
    __tablename__ = "resumes"
    __table_args__ = (
        Index("ix_resumes_user_created", "user_id", text("created_at DESC")),
    )

    user_id: str = Field(index=True)
    job_id: uuid.UUID | None = Field(default=None, foreign_key="jobs.id", ondelete="SET NULL")
    content_json: dict | None = Field(default=None, sa_column=Column(SA_JSON))
    ats_score: float | None = Field(default=None)
    ats_breakdown: dict | None = Field(default=None, sa_column=Column(SA_JSON))
    template_id: str | None = Field(default=None)
    status: str | None = Field(default=None)
    pdf_s3_key: str | None = Field(default=None)
    pdf_url: str | None = Field(default=None)
    uploaded_resume_s3_key: str | None = Field(default=None)
