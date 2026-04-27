import { api } from "@/lib/api";
import type {
  InterviewChatRequest,
  InterviewChatResponse,
  InterviewPrepListResponse,
  InterviewPrepStatusResponse,
  InterviewSessionDetail,
  InterviewSessionListResponse,
  InterviewSetupRequest,
  InterviewSetupResponse,
} from "@/types/interview";

export async function setupInterviewPrep(
  data: InterviewSetupRequest,
): Promise<InterviewSetupResponse> {
  return api.post<InterviewSetupResponse>("/api/interview/setup", data);
}

export async function listInterviewPreps(
  limit: number = 20,
  offset: number = 0,
): Promise<InterviewPrepListResponse> {
  return api.get<InterviewPrepListResponse>(
    `/api/interview/preps?limit=${limit}&offset=${offset}`,
  );
}

export async function getInterviewPrepStatus(
  id: string,
): Promise<InterviewPrepStatusResponse> {
  return api.get<InterviewPrepStatusResponse>(`/api/interview/preps/${id}/status`);
}

export async function sendChatMessage(
  data: InterviewChatRequest,
): Promise<InterviewChatResponse> {
  return api.post<InterviewChatResponse>("/api/interview/chat", data);
}

export async function listInterviewSessions(
  limit: number = 20,
  offset: number = 0,
): Promise<InterviewSessionListResponse> {
  return api.get<InterviewSessionListResponse>(
    `/api/interview/sessions?limit=${limit}&offset=${offset}`,
  );
}

export async function getInterviewSession(
  id: string,
): Promise<InterviewSessionDetail> {
  return api.get<InterviewSessionDetail>(`/api/interview/sessions/${id}`);
}

export async function deleteInterviewPrep(id: string): Promise<void> {
  await api.delete(`/api/interview/preps/${id}`);
}
