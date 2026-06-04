import uuid
from datetime import datetime
from typing import Union

from pydantic import BaseModel, Field, model_validator


class ResumeGenerateRequest(BaseModel):
    job_id: uuid.UUID | None = None
    job_description: str | None = Field(default=None, max_length=10000)
    force_regenerate: bool = False

    @model_validator(mode="after")
    def check_at_least_one_source(self) -> "ResumeGenerateRequest":
        if self.job_id is None and not self.job_description:
            raise ValueError("At least one of job_id or job_description must be provided")
        return self


class ResumeGenerateManualRequest(BaseModel):
    job_description: str = Field(min_length=50, max_length=10000)
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)


class ResumeGenerateResponse(BaseModel):
    resume_id: uuid.UUID
    status: str
    ats_score: float | None = None
    content_json: dict | None = None


class ResumeStatusResponse(BaseModel):
    resume_id: uuid.UUID
    status: str
    progress_step: str | None = None
    ats_score: float | None = None


class ResumeListItem(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_title: str | None = None
    company_name: str | None = None
    ats_score: float | None = None
    created_at: datetime


class ResumeListResponse(BaseModel):
    resumes: list[ResumeListItem]
    total: int


class ResumeResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_title: str | None = None
    company_name: str | None = None
    ats_score: float | None = None
    ats_breakdown: dict | None = None
    content_json: dict | None = None
    pdf_url: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
    status: str | None = None


