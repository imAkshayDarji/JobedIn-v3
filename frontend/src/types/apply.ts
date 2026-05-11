export type ApplyStep =
  | "load_profile"
  | "generate_resume"
  | "save_resume"
  | "generate_cover_letter"
  | "filling_form"
  | "submitting"
  | "verifying";

export const APPLY_STEP_LABELS: Record<ApplyStep, string> = {
  load_profile: "Loading profile",
  generate_resume: "Generating resume",
  save_resume: "Saving resume",
  generate_cover_letter: "Generating cover letter",
  filling_form: "Filling application form",
  submitting: "Submitting application",
  verifying: "Verifying submission",
};

export const APPLY_STEPS: ApplyStep[] = [
  "load_profile",
  "generate_resume",
  "save_resume",
  "generate_cover_letter",
  "filling_form",
  "submitting",
  "verifying",
];

export interface ApplySingleRequest {
  application_id: string;
}

export interface ApplySingleResponse {
  application_id: string;
  task_id: string;
  message: string;
}

export interface ApplyBulkRequest {
  application_ids: string[];
}

export interface ApplyBulkResponse {
  bulk_task_id: string;
  application_ids: string[];
  message: string;
}

export interface ApplyStatusResponse {
  application_id: string;
  status: string;
  step: string | null;
  error: string | null;
  notes: string | null;
  resume_id: string | null;
  cover_letter_id: string | null;
  screenshot_path: string | null;
  manual_url: string | null;
}

export interface ApplyBulkStatusResponse {
  bulk_task_id: string;
  total: number;
  completed: number;
  failed: number;
  manual_required: number;
  pending: number;
  results: ApplyStatusResponse[];
}

export interface ApplySSEEvent {
  event: string;
  application_id: string;
  step: string | null;
  status: string | null;
  error: string | null;
  notes?: string | null;
  manual_url?: string | null;
}
