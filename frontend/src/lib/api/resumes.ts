import { api } from "@/lib/api";
import type {
  ResumeGenerateRequest,
  ResumeGenerateManualRequest,
  ResumeGenerateResponse,
  ResumeStatusResponse,
  ResumeListResponse,
  ResumeResponse,
} from "@/types/resume";

export async function generateResume(
  data: ResumeGenerateRequest,
): Promise<ResumeGenerateResponse> {
  return api.post<ResumeGenerateResponse>("/api/resumes/generate", data);
}

export async function generateResumeManual(
  data: ResumeGenerateManualRequest,
): Promise<ResumeGenerateResponse> {
  return api.post<ResumeGenerateResponse>("/api/resumes/generate-manual", data);
}

export async function getResumeStatus(
  id: string,
): Promise<ResumeStatusResponse> {
  return api.get<ResumeStatusResponse>(`/api/resumes/${id}/status`);
}

export async function listResumes(
  limit: number = 20,
  offset: number = 0,
): Promise<ResumeListResponse> {
  return api.get<ResumeListResponse>(
    `/api/resumes?limit=${limit}&offset=${offset}`,
  );
}

export async function getResume(id: string): Promise<ResumeResponse> {
  return api.get<ResumeResponse>(`/api/resumes/${id}`);
}

export async function deleteResume(id: string): Promise<void> {
  await api.delete(`/api/resumes/${id}`);
}
