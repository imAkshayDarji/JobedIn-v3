import uuid
from datetime import date

from sqlmodel import Field, Relationship

from app.models.base import TimestampModel


class Project(TimestampModel, table=True):
    __tablename__ = "projects"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    name: str
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    start_date: date | None = Field(default=None)
    end_date: date | None = Field(default=None)
    technologies: str | None = Field(default=None)

    candidate: "CandidateProfile" = Relationship(back_populates="projects")  # type: ignore[assignment]
