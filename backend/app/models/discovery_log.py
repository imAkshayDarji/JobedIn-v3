from datetime import datetime

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSON
from sqlmodel import Field

from app.models.base import TimestampModel


class DiscoveryLog(TimestampModel, table=True):
    __tablename__ = "discovery_logs"

    sources: list = Field(sa_column=Column(JSON, nullable=False))
    keywords: list = Field(sa_column=Column(JSON, nullable=False))
    location: str | None = Field(default=None)
    total_found: int = Field(default=0)
    new_count: int = Field(default=0)
    updated_count: int = Field(default=0)
    skipped_count: int = Field(default=0)
    errors: list | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    duration_seconds: float | None = Field(default=None)
