import uuid
from datetime import datetime

from sqlalchemy import Index, text
from sqlmodel import Field

from app.models.base import TimestampModel


class AITokenUsage(TimestampModel, table=True):
    __tablename__ = "ai_token_usage"
    __table_args__ = (
        Index("ix_ai_token_usage_user_created", "user_id", text("created_at DESC")),
    )

    user_id: uuid.UUID = Field(index=True)
    task: str
    model_used: str
    prompt_tokens: int = Field(default=0)
    completion_tokens: int = Field(default=0)
    total_tokens: int = Field(default=0)
    latency_ms: float = Field(default=0.0)
