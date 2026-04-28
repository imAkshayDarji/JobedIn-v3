export interface MatchBreakdown {
  skills_score: number;
  experience_score: number;
  role_relevance_score: number;
  location_score: number;
}

export interface JobMatchScore {
  job_id: string;
  match_score: number;
  breakdown: MatchBreakdown;
  matched_skills: string[];
  missing_skills: string[];
}

export interface JobListItem {
  id: string;
  title: string;
  company: string;
  location: string | null;
  source: string;
  source_url: string | null;
  salary_min: number | null;
  salary_max: number | null;
  experience_level: string | null;
  job_type: string | null;
  remote_policy: string | null;
  scraped_at: string | null;
  created_at: string | null;
  match_score: number | null;
  is_saved: boolean;
}

export interface JobListResponse {
  jobs: JobListItem[];
  total: number;
}

export interface JobDetail {
  id: string;
  source: string;
  source_url: string | null;
  external_id: string | null;
  title: string;
  company: string;
  description: string | null;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  location: string | null;
  experience_level: string | null;
  job_type: string | null;
  remote_policy: string | null;
  ats_platform: string | null;
  apply_url: string | null;
  scraped_at: string | null;
  created_at: string | null;
  alternate_sources: Record<string, unknown>[] | null;
  match_score: number | null;
  match_breakdown: MatchBreakdown | null;
  is_saved: boolean;
}

export interface SavedJob {
  application_id: string;
  job_id: string;
  title: string;
  company: string;
  location: string | null;
  source: string;
  saved_at: string | null;
}

export interface SavedJobsResponse {
  jobs: SavedJob[];
  total: number;
}

export interface MatchStatus {
  status: string;
  scored_count: number;
  total_count: number;
  results: JobMatchScore[] | null;
}

export interface DiscoverRequest {
  keywords?: string[] | null;
  location?: string | null;
  sources?: string[] | null;
}

export interface DiscoverResponse {
  job_id: string;
  message: string;
}

export interface DiscoverStatusResponse {
  status: string;
  last_scraped_at: string | null;
}

export interface SourceStatus {
  name: string;
  type: string;
  available: boolean;
  detail: string | null;
}

export interface SourcesStatusResponse {
  sources: SourceStatus[];
}
