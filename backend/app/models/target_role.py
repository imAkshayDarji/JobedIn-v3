import uuid

from sqlmodel import Field

from app.models.base import TimestampModel


class TargetRole(TimestampModel, table=True):
    __tablename__ = "target_roles"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    title: str
    priority: int = Field(default=0)
    keywords: str | None = Field(default=None)
