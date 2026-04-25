import uuid
from datetime import date

from sqlmodel import Field, Relationship

from app.models.base import TimestampModel


class Certification(TimestampModel, table=True):
    __tablename__ = "certifications"

    candidate_id: uuid.UUID = Field(foreign_key="candidate_profiles.id", ondelete="CASCADE")
    name: str
    issuer: str | None = Field(default=None)
    issue_date: date | None = Field(default=None)
    expiry_date: date | None = Field(default=None)
    credential_url: str | None = Field(default=None)

    candidate: "CandidateProfile" = Relationship(back_populates="certifications")  # type: ignore[assignment]
