import uuid

from sqlmodel import Field

from app.models.base import TimestampModel


class Skill(TimestampModel, table=True):
    __tablename__ = "skills"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    name: str
    category: str | None = Field(default=None)
    proficiency: str | None = Field(default=None)
