import uuid
from enum import StrEnum

from pydantic import BaseModel


class ATSDifficultyEnum(StrEnum):
    easy_apply = "easy_apply"
    multi_step = "multi_step"
    manual_only = "manual_only"


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
