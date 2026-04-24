import uuid

from sqlmodel import Field

from app.models.base import TimestampModel


class Language(TimestampModel, table=True):
    __tablename__ = "languages"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    name: str
    proficiency: str | None = Field(default=None)
