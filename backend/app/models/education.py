import uuid
from datetime import date

from sqlmodel import Field, Relationship

from app.models.base import TimestampModel


class Education(TimestampModel, table=True):
    __tablename__ = "educations"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    institution: str
    degree: str
    field_of_study: str | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    grade: str | None = Field(default=None)
    description: str | None = Field(default=None)

    candidate: "CandidateProfile" = Relationship(back_populates="education")  # type: ignore[assignment]
