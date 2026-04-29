export interface ProfileSummary {
  first_name: string | null;
  experience_level: string | null;
  onboarding_completed: boolean;
}

export interface DashboardStats {
  jobs_matched: number;
  high_match_count: number;
  avg_match_score: number | null;
  applications_count: number;
  applications_by_status: Record<string, number>;
  resumes_count: number;
  resumes_completed: number;
  avg_ats_score: number | null;
  cover_letters_count: number;
  interview_preps_count: number;
  interview_sessions_count: number;
  interview_sessions_completed: number;
  avg_session_score: number | null;
}

export interface ActivityItem {
  type: "application" | "resume" | "cover_letter" | "interview_session";
  id: string;
  title: string;
  status: string | null;
  job_id: string | null;
  created_at: string;
}

export interface DashboardResponse {
  profile: ProfileSummary | null;
  stats: DashboardStats;
  recent_activity: ActivityItem[];
}
