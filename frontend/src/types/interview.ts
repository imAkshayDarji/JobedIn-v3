export interface InterviewQuestion {
  question: string;
  category: "company_research" | "technical" | "behavioral" | "culture_fit";
  difficulty: 1 | 2 | 3;
  follow_up_hints: string[];
}

export interface InterviewSetupRequest {
  job_id?: string;
  job_description?: string;
  job_title?: string;
  company_name?: string;
}

export interface InterviewSetupResponse {
  prep_id: string;
  status: "generating" | "completed" | "failed";
}

export interface InterviewPrepStatusResponse {
  prep_id: string;
  status: "generating" | "completed" | "failed";
  question_count: number;
}

export interface InterviewPrepListItem {
  id: string;
  job_id: string | null;
  job_title: string | null;
  company_name: string | null;
  status: string;
  question_count: number;
  created_at: string;
}

export interface InterviewPrepListResponse {
  preps: InterviewPrepListItem[];
  total: number;
}

export interface ChatEvaluation {
  score: number;
  strengths: string[];
  improvements: string[];
  coaching_tip: string;
  sample_answer: string;
}

export interface ChatQuestion {
  question: string;
  category: string;
  difficulty: number;
  follow_up_hints: string[];
}

export interface InterviewChatRequest {
  prep_id: string;
  session_id?: string;
  answer?: string;
}

export interface InterviewChatResponse {
  session_id: string;
  evaluation: ChatEvaluation | null;
  next_question: ChatQuestion | null;
  session_complete: boolean;
  difficulty: number;
  overall_feedback: string | null;
}

export interface SessionMessage {
  role: "question" | "user" | "coach" | "summary";
  content: string;
  score: number | null;
  category: string | null;
  difficulty: number | null;
}

export interface InterviewSessionDetail {
  id: string;
  prep_id: string;
  status: string;
  current_difficulty: number;
  questions_answered: number;
  overall_score: number | null;
  messages: SessionMessage[];
  overall_feedback: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface InterviewSessionListItem {
  id: string;
  prep_id: string;
  job_title: string | null;
  company_name: string | null;
  status: string;
  questions_answered: number;
  overall_score: number | null;
  created_at: string;
}

export interface InterviewSessionListResponse {
  sessions: InterviewSessionListItem[];
  total: number;
}
