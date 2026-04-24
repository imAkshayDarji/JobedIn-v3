import uuid
from datetime import date

from sqlmodel import Field

from app.models.base import TimestampModel


class Experience(TimestampModel, table=True):
    __tablename__ = "experiences"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    company: str
    title: str
    location: str | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    description: str | None = Field(default=None)
    is_current: bool = Field(default=False)
