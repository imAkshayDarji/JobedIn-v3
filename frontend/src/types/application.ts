export type ApplicationStatus =
  | "saved"
  | "generating"
  | "ready"
  | "applied"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export interface ApplicationJobInfo {
  id: string;
  title: string;
  company: string;
  location: string | null;
  source: string;
  source_url: string | null;
  salary_min: number | null;
  salary_max: number | null;
  remote_policy: string | null;
  experience_level: string | null;
}

export interface ApplicationListItem {
  id: string;
  status: ApplicationStatus;
  applied_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  job: ApplicationJobInfo;
  match_score: number | null;
  resume_id: string | null;
  cover_letter_id: string | null;
  interview_prep_id: string | null;
}

export interface ApplicationListResponse {
  applications: ApplicationListItem[];
  total: number;
}

export interface ApplicationDetail {
  id: string;
  status: ApplicationStatus;
  applied_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  job: ApplicationJobInfo;
  match_score: number | null;
  match_breakdown: Record<string, number> | null;
  resume_id: string | null;
  cover_letter_id: string | null;
  interview_prep_id: string | null;
}

export interface ApplicationStats {
  total: number;
  by_status: Record<string, number>;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  notes?: string;
}
