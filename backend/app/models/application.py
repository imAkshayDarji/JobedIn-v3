import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import ApplicationStatus, TimestampModel


class Application(TimestampModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_applications_user_job"),
    )

    user_id: uuid.UUID = Field(index=True)
    job_id: uuid.UUID = Field(foreign_key="jobs.id", ondelete="CASCADE")
    status: ApplicationStatus = Field(default=ApplicationStatus.saved)
    applied_at: datetime | None = Field(default=None)
    notes: str | None = Field(default=None)

    ats_platform: str | None = Field(default=None)
    ats_detection_method: str | None = Field(default=None)
    ats_confidence: float | None = Field(default=None)
    ats_form_url: str | None = Field(default=None)
    ats_detected_fields: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    ats_screenshot_path: str | None = Field(default=None)
    ats_detection_error: str | None = Field(default=None)
    ats_difficulty: str | None = Field(default=None)
