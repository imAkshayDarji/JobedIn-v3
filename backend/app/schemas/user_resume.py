from datetime import datetime

from pydantic import BaseModel, Field


class UserResumeMetadataResponse(BaseModel):
    has_uploaded_resume: bool
    filename: str | None = None
    uploaded_at: datetime | None = None
    text_preview: str | None = Field(
        default=None,
        description="First 500 characters of extracted text",
    )


class UserResumeUploadResponse(BaseModel):
    has_uploaded_resume: bool = True
    filename: str
    uploaded_at: datetime
    text_preview: str | None = None
