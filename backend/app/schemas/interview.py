import uuid
from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class InterviewSetupRequest(BaseModel):
    job_id: uuid.UUID | None = None
    job_description: str | None = Field(default=None, max_length=10000)
    job_title: str | None = Field(default=None, max_length=200)
    company_name: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def check_at_least_one_source(self) -> "InterviewSetupRequest":
        if self.job_id is None and not self.job_description:
            raise ValueError("At least one of job_id or job_description must be provided")
        return self


class InterviewSetupResponse(BaseModel):
    prep_id: uuid.UUID
    status: str


class InterviewPrepStatusResponse(BaseModel):
    prep_id: uuid.UUID
    status: str
    question_count: int = 0


class InterviewChatRequest(BaseModel):
    prep_id: uuid.UUID
    session_id: uuid.UUID | None = None
    answer: str = Field(default="", max_length=5000)


class ChatEvaluation(BaseModel):
    score: float
    strengths: list[str]
    improvements: list[str]
    coaching_tip: str
    sample_answer: str


class ChatQuestion(BaseModel):
    question: str
    category: str
    difficulty: int
    follow_up_hints: list[str] = Field(default_factory=list)


class InterviewChatResponse(BaseModel):
    session_id: uuid.UUID
    evaluation: ChatEvaluation | None = None
    next_question: ChatQuestion | None = None
    session_complete: bool = False
    difficulty: int = 1
    overall_feedback: str | None = None


class InterviewPrepListItem(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID | None = None
    job_title: str | None = None
    company_name: str | None = None
    status: str
    question_count: int = 0
    created_at: datetime


class InterviewPrepListResponse(BaseModel):
    preps: list[InterviewPrepListItem]
    total: int


class SessionMessage(BaseModel):
    role: str
    content: str
    score: float | None = None
    category: str | None = None
    difficulty: int | None = None


class InterviewSessionDetail(BaseModel):
    id: uuid.UUID
    prep_id: uuid.UUID
    status: str
    current_difficulty: int
    questions_answered: int
    overall_score: float | None = None
    messages: list[SessionMessage] = Field(default_factory=list)
    overall_feedback: str | None = None
    completed_at: datetime | None = None
    created_at: datetime


class InterviewSessionListItem(BaseModel):
    id: uuid.UUID
    prep_id: uuid.UUID
    job_title: str | None = None
    company_name: str | None = None
    status: str
    questions_answered: int
    overall_score: float | None = None
    created_at: datetime


class InterviewSessionListResponse(BaseModel):
    sessions: list[InterviewSessionListItem]
    total: int
