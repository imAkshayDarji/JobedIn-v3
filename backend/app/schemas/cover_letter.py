import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class CoverLetterGenerateRequest(BaseModel):
    job_id: uuid.UUID | None = None
    job_description: str | None = Field(default=None, max_length=10000)
    tone: str | None = Field(default="professional", pattern="^(professional|casual|enthusiastic)$")

    @model_validator(mode="after")
    def check_at_least_one_source(self) -> "CoverLetterGenerateRequest":
        if self.job_id is None and not self.job_description:
            raise ValueError("At least one of job_id or job_description must be provided")
        return self


class CoverLetterGenerateManualRequest(BaseModel):
    job_description: str = Field(min_length=50, max_length=10000)
    company_name: str | None = Field(default=None, max_length=200)
    job_title: str | None = Field(default=None, max_length=200)
    tone: str | None = Field(default="professional", pattern="^(professional|casual|enthusiastic)$")


class CoverLetterGenerateResponse(BaseModel):
    cover_letter_id: uuid.UUID
    status: str
    content_json: dict | None = None


class CoverLetterStatusResponse(BaseModel):
    cover_letter_id: uuid.UUID
    status: str
    tone: str | None = None


class CoverLetterListItem(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_title: str | None = None
    company_name: str | None = None
    tone: str | None = None
    created_at: datetime


class CoverLetterListResponse(BaseModel):
    cover_letters: list[CoverLetterListItem]
    total: int


class CoverLetterResponse(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_title: str | None = None
    company_name: str | None = None
    content: str | None = None
    content_json: dict | None = None
    tone: str | None = None
    ai_model_used: str | None = None
    status: str | None = None
    created_at: datetime
    updated_at: datetime | None = None
