from datetime import datetime

from pydantic import BaseModel


class ProfileSummary(BaseModel):
    first_name: str | None
    experience_level: str | None
    onboarding_completed: bool


class DashboardStats(BaseModel):
    jobs_matched: int
    high_match_count: int
    avg_match_score: float | None
    applications_count: int
    applications_by_status: dict[str, int]
    resumes_count: int
    resumes_completed: int
    avg_ats_score: float | None
    cover_letters_count: int
    interview_preps_count: int
    interview_sessions_count: int
    interview_sessions_completed: int
    avg_session_score: float | None


class ActivityItem(BaseModel):
    type: str
    id: str
    title: str
    status: str | None
    job_id: str | None
    created_at: datetime


class DashboardResponse(BaseModel):
    profile: ProfileSummary | None
    stats: DashboardStats
    recent_activity: list[ActivityItem]
