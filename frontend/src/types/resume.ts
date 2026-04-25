export interface ResumeGenerateRequest {
  job_id?: string;
  job_description?: string;
}

export interface ResumeGenerateManualRequest {
  job_description: string;
  company_name?: string;
  job_title?: string;
}

export interface ResumeGenerateResponse {
  resume_id: string;
  status: "generating" | "completed" | "failed";
  ats_score: number | null;
  content_json: Record<string, unknown> | null;
}

export interface ResumeStatusResponse {
  resume_id: string;
  status: "generating" | "completed" | "failed";
  progress_step: string | null;
  ats_score: number | null;
}

export interface ResumeListItem {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  ats_score: number | null;
  created_at: string;
}

export interface ResumeListResponse {
  resumes: ResumeListItem[];
  total: number;
}

export interface ResumeResponse {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  ats_score: number | null;
  ats_breakdown: Record<string, unknown> | null;
  content_json: Record<string, unknown> | null;
  created_at: string;
  updated_at: string | null;
  status: string | null;
}

export interface ResumeSection {
  title: string;
  order: number;
  bullet_points: {
    text: string;
    keywords_included: string[];
  }[];
  content: string | null;
}

export interface ResumeContent {
  sections: ResumeSection[];
  target_keywords_covered: string[];
  overall_keyword_coverage: number;
}

export interface ATSKeywordCheck {
  keyword: string;
  found: boolean;
  count: number;
}

export interface ATSSectionCheck {
  section: string;
  present: boolean;
  score: number;
}

export interface ATSResult {
  overall_score: number;
  keyword_score: number;
  section_score: number;
  keyword_checks: ATSKeywordCheck[];
  section_checks: ATSSectionCheck[];
  missing_keywords: string[];
  suggestions: string[];
}
