import datetime
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class ApplicationStatusEnum(str, Enum):
    saved = "saved"
    generating = "generating"
    ready = "ready"
    applied = "applied"
    screening = "screening"
    interview = "interview"
    offer = "offer"
    rejected = "rejected"
    withdrawn = "withdrawn"


class ApplicationUpdate(BaseModel):
    status: ApplicationStatusEnum | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationNotesUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=2000)


class ApplicationJobInfo(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    source: str
    source_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    remote_policy: str | None = None
    experience_level: str | None = None


class ApplicationListItem(BaseModel):
    id: uuid.UUID
    status: str
    applied_at: datetime.datetime | None = None
    notes: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    job: ApplicationJobInfo
    match_score: float | None = None
    resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    interview_prep_id: uuid.UUID | None = None


class ApplicationListResponse(BaseModel):
    applications: list[ApplicationListItem]
    total: int


class ApplicationDetail(BaseModel):
    id: uuid.UUID
    status: str
    applied_at: datetime.datetime | None = None
    notes: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    job: ApplicationJobInfo
    match_score: float | None = None
    match_breakdown: dict | None = None
    resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    interview_prep_id: uuid.UUID | None = None
    ats_form_url: str | None = None
    ats_screenshot_path: str | None = None


class ApplicationStats(BaseModel):
    total: int
    by_status: dict[str, int]
