import uuid
from datetime import datetime

from sqlalchemy import UniqueConstraint
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
