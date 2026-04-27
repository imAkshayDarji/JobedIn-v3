import datetime
import uuid

from pydantic import BaseModel, Field


class JobDiscoverRequest(BaseModel):
    keywords: list[str] | None = None
    location: str | None = None


class JobDiscoverResponse(BaseModel):
    job_id: str
    message: str


class JobDiscoverStatusResponse(BaseModel):
    status: str
    last_scraped_at: str | None = None


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    source: str
    source_url: str | None = None
    scraped_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None


class JobListResponse(BaseModel):
    jobs: list[JobListItem]
    total: int


class JobDetailResponse(BaseModel):
    id: uuid.UUID
    source: str
    source_url: str | None = None
    external_id: str | None = None
    title: str
    company: str
    description: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    location: str | None = None
    experience_level: str | None = None
    job_type: str | None = None
    remote_policy: str | None = None
    ats_platform: str | None = None
    apply_url: str | None = None
    scraped_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None


class SavedJobListItem(BaseModel):
    application_id: uuid.UUID
    job_id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    source: str
    saved_at: datetime.datetime | None = None


class SavedJobsResponse(BaseModel):
    jobs: list[SavedJobListItem]
    total: int
