import uuid

from pydantic import BaseModel


class MatchBreakdown(BaseModel):
    skills_score: float
    experience_score: float
    role_relevance_score: float
    location_score: float


class JobMatchResultSchema(BaseModel):
    job_id: uuid.UUID
    match_score: float
    breakdown: MatchBreakdown
    matched_skills: list[str]
    missing_skills: list[str]


class MatchRequest(BaseModel):
    job_ids: list[uuid.UUID] | None = None


class MatchResponse(BaseModel):
    task_id: str
    message: str


class MatchStatusResponse(BaseModel):
    status: str
    scored_count: int
    total_count: int
    results: list[JobMatchResultSchema] | None = None


class JobScoreResponse(BaseModel):
    job_id: uuid.UUID
    match_score: float
    breakdown: MatchBreakdown
    matched_skills: list[str]
    missing_skills: list[str]
