import datetime
import uuid

from pydantic import BaseModel, Field

from app.models.base import JobSource

VALID_SOURCE_NAMES = {s.value for s in JobSource}


class JobDiscoverRequest(BaseModel):
    keywords: list[str] | None = None
    location: str | None = None
    sources: list[str] | None = None

    def validated_sources(self) -> list[str] | None:
        if self.sources is None:
            return None
        invalid = [s for s in self.sources if s not in VALID_SOURCE_NAMES]
        if invalid:
            raise ValueError(f"Invalid sources: {', '.join(invalid)}. Valid: {', '.join(sorted(VALID_SOURCE_NAMES))}")
        return self.sources


class JobDiscoverResponse(BaseModel):
    job_id: str
    message: str


class MultiSourceDiscoverResponse(BaseModel):
    job_id: str
    message: str
    sources: list[str]


class JobDiscoverStatusResponse(BaseModel):
    status: str
    last_scraped_at: str | None = None


class SourceStatusItem(BaseModel):
    name: str
    type: str
    available: bool
    detail: str | None = None


class SourcesStatusResponse(BaseModel):
    sources: list[SourceStatusItem]


class JobListItem(BaseModel):
    id: uuid.UUID
    title: str
    company: str
    location: str | None = None
    source: str
    source_url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    experience_level: str | None = None
    job_type: str | None = None
    remote_policy: str | None = None
    scraped_at: datetime.datetime | None = None
    created_at: datetime.datetime | None = None
    match_score: float | None = None
    is_saved: bool = False
    application_id: uuid.UUID | None = None


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
    alternate_sources: list[dict] | None = None
    match_score: float | None = None
    match_breakdown: "MatchBreakdownSchema | None" = None
    is_saved: bool = False


class MatchBreakdownSchema(BaseModel):
    skills_score: float
    experience_score: float
    role_relevance_score: float
    location_score: float


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
