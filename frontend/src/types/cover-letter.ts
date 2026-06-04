export interface CoverLetterGenerateRequest {
  job_id?: string;
  job_description?: string;
  tone?: "professional" | "casual" | "enthusiastic";
  force_regenerate?: boolean;
}

export interface CoverLetterGenerateManualRequest {
  job_description: string;
  company_name?: string;
  job_title?: string;
  tone?: "professional" | "casual" | "enthusiastic";
}

export interface CoverLetterGenerateResponse {
  cover_letter_id: string;
  status: "generating" | "completed" | "failed";
  content_json: Record<string, unknown> | null;
}

export interface CoverLetterStatusResponse {
  cover_letter_id: string;
  status: "generating" | "completed" | "failed";
  tone: string | null;
}

export interface CoverLetterListItem {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  tone: string | null;
  created_at: string;
}

export interface CoverLetterListResponse {
  cover_letters: CoverLetterListItem[];
  total: number;
}

export interface CoverLetterResponse {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  content: string | null;
  content_json: Record<string, unknown> | null;
  pdf_url?: string | null;
  tone: string | null;
  ai_model_used: string | null;
  status: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface CoverLetterParagraph {
  heading: string | null;
  body: string;
}

export interface CoverLetterContent {
  paragraphs: CoverLetterParagraph[];
  tone_used: string;
  keywords_addressed: string[];
  full_text: string;
}
