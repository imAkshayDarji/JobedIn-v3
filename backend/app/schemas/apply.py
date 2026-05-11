import uuid
from enum import StrEnum

from pydantic import BaseModel, Field


class ATSDifficultyEnum(StrEnum):
    easy_apply = "easy_apply"
    multi_step = "multi_step"
    manual_only = "manual_only"
    manual_assist = "manual_assist"


class ATSDetectRequest(BaseModel):
    job_id: uuid.UUID
    apply_url: str | None = None


class ATSDetectResponse(BaseModel):
    application_id: uuid.UUID
    task_id: str
    message: str


class ATSDetectionStatusResponse(BaseModel):
    application_id: uuid.UUID
    job_id: uuid.UUID
    status: str
    ats_platform: str | None = None
    ats_detection_method: str | None = None
    ats_confidence: float | None = None
    ats_form_url: str | None = None
    ats_detected_fields: list[str] | None = None
    ats_screenshot_path: str | None = None
    ats_detection_error: str | None = None
    ats_difficulty: ATSDifficultyEnum | None = None


class ApplySingleRequest(BaseModel):
    application_id: uuid.UUID


class ApplySingleResponse(BaseModel):
    application_id: uuid.UUID
    task_id: str
    message: str


class ApplyBulkRequest(BaseModel):
    application_ids: list[uuid.UUID] = Field(..., max_length=10)


class ApplyBulkResponse(BaseModel):
    bulk_task_id: str
    application_ids: list[uuid.UUID]
    message: str


class ApplyStatusResponse(BaseModel):
    application_id: uuid.UUID
    status: str
    step: str | None = None
    error: str | None = None
    notes: str | None = None
    resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    screenshot_path: str | None = None
    manual_url: str | None = None


class ApplyBulkStatusResponse(BaseModel):
    bulk_task_id: str
    total: int
    completed: int
    failed: int
    manual_required: int
    pending: int
    results: list[ApplyStatusResponse]


class ApplyOrchestratorResult(BaseModel):
    application_id: uuid.UUID
    success: bool
    status: str
    resume_id: uuid.UUID | None = None
    cover_letter_id: uuid.UUID | None = None
    screenshot_path: str | None = None
    manual_url: str | None = None
    error: str | None = None
    steps_completed: list[str]
    total_latency_ms: int


class ApplySSEEvent(BaseModel):
    event: str
    application_id: uuid.UUID
    step: str | None = None
    status: str | None = None
    error: str | None = None
    notes: str | None = None
    manual_url: str | None = None
