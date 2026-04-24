import uuid

from sqlmodel import Field

from app.models.base import TimestampModel


class CoverLetter(TimestampModel, table=True):
    __tablename__ = "cover_letters"

    user_id: uuid.UUID = Field(index=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    content: str
    tone: str | None = Field(default=None)
    ai_model_used: str | None = Field(default=None)
