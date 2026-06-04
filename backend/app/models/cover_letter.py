import uuid

from sqlalchemy import Column, Index, JSON as SA_JSON, text
from sqlmodel import Field

from app.models.base import TimestampModel


class CoverLetter(TimestampModel, table=True):
    __tablename__ = "cover_letters"
    __table_args__ = (
        Index("ix_cover_letters_user_created", "user_id", text("created_at DESC")),
    )

    user_id: str = Field(index=True)
    job_id: uuid.UUID | None = Field(default=None, foreign_key="jobs.id", ondelete="SET NULL")
    job_description: str | None = Field(default=None)
    content: str | None = Field(default=None)
    content_json: dict | None = Field(default=None, sa_column=Column(SA_JSON))
    tone: str | None = Field(default=None)
    ai_model_used: str | None = Field(default=None)
    status: str | None = Field(default=None)
    pdf_s3_key: str | None = Field(default=None)
    pdf_url: str | None = Field(default=None)
