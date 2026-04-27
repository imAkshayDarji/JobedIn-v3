import { api } from "@/lib/api";
import type {
  CoverLetterGenerateRequest,
  CoverLetterGenerateManualRequest,
  CoverLetterGenerateResponse,
  CoverLetterStatusResponse,
  CoverLetterListResponse,
  CoverLetterResponse,
} from "@/types/cover-letter";

export async function generateCoverLetter(
  data: CoverLetterGenerateRequest,
): Promise<CoverLetterGenerateResponse> {
  return api.post<CoverLetterGenerateResponse>("/api/cover-letters/generate", data);
}

export async function generateCoverLetterManual(
  data: CoverLetterGenerateManualRequest,
): Promise<CoverLetterGenerateResponse> {
  return api.post<CoverLetterGenerateResponse>("/api/cover-letters/generate-manual", data);
}

export async function getCoverLetterStatus(
  id: string,
): Promise<CoverLetterStatusResponse> {
  return api.get<CoverLetterStatusResponse>(`/api/cover-letters/${id}/status`);
}

export async function listCoverLetters(
  limit: number = 20,
  offset: number = 0,
): Promise<CoverLetterListResponse> {
  return api.get<CoverLetterListResponse>(
    `/api/cover-letters?limit=${limit}&offset=${offset}`,
  );
}

export async function getCoverLetter(id: string): Promise<CoverLetterResponse> {
  return api.get<CoverLetterResponse>(`/api/cover-letters/${id}`);
}

export async function deleteCoverLetter(id: string): Promise<void> {
  await api.delete(`/api/cover-letters/${id}`);
}
