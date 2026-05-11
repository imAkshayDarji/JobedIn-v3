export type ApplicationStatus =
  | "saved"
  | "generating"
  | "ready"
  | "applying"
  | "applied"
  | "applied_with_issues"
  | "manual_required"
  | "failed"
  | "screening"
  | "interview"
  | "offer"
  | "rejected"
  | "withdrawn";

export const STATUS_STYLES: Record<string, string> = {
  saved: "bg-gray-100 text-gray-700",
  generating: "bg-yellow-100 text-yellow-800",
  ready: "bg-blue-100 text-blue-800",
  applying: "bg-orange-100 text-orange-800",
  applied: "bg-indigo-100 text-indigo-800",
  applied_with_issues: "bg-yellow-100 text-yellow-800",
  manual_required: "bg-amber-100 text-amber-800",
  failed: "bg-red-100 text-red-800",
  screening: "bg-purple-100 text-purple-800",
  interview: "bg-cyan-100 text-cyan-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-500",
};

export const COLUMN_COLORS: Record<string, string> = {
  saved: "border-t-gray-400",
  generating: "border-t-yellow-400",
  ready: "border-t-blue-400",
  applying: "border-t-orange-400",
  applied: "border-t-indigo-400",
  applied_with_issues: "border-t-yellow-400",
  manual_required: "border-t-amber-400",
  failed: "border-t-red-400",
  screening: "border-t-purple-400",
  interview: "border-t-cyan-400",
  offer: "border-t-green-400",
  rejected: "border-t-red-400",
  withdrawn: "border-t-gray-300",
};

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
  ats_form_url: string | null;
  ats_screenshot_path: string | null;
}

export interface ApplicationStats {
  total: number;
  by_status: Record<string, number>;
}

export interface ApplicationUpdate {
  status?: ApplicationStatus;
  notes?: string;
}
