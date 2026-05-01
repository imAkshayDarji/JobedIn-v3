import uuid
from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel


class ExperienceLevel(StrEnum):
    student = "student"
    fresher = "fresher"
    junior = "junior"
    mid = "mid"
    senior = "senior"
    lead = "lead"
    executive = "executive"


class JobSource(StrEnum):
    linkedin = "linkedin"
    adzuna = "adzuna"
    jsearch = "jsearch"
    remotive = "remotive"
    reed = "reed"


class ApplicationStatus(StrEnum):
    saved = "saved"
    generating = "generating"
    ready = "ready"
    applying = "applying"
    applied = "applied"
    applied_with_issues = "applied_with_issues"
    manual_required = "manual_required"
    failed = "failed"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class RemotePolicy(StrEnum):
    remote = "remote"
    hybrid = "hybrid"
    onsite = "onsite"


class TimestampModel(SQLModel):
    id: uuid.UUID | None = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(default_factory=datetime.utcnow)
    updated_at: datetime | None = Field(default_factory=datetime.utcnow)
