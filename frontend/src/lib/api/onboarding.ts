import { api } from "@/lib/api";
import type {
  OnboardingSaveRequest,
  OnboardingSaveResponse,
  OnboardingStatusResponse,
  ResumeUploadResponse,
} from "@/types/onboarding";

export async function getOnboardingStatus(): Promise<OnboardingStatusResponse> {
  return api.get<OnboardingStatusResponse>("/api/onboarding/status");
}

export async function saveOnboarding(
  data: OnboardingSaveRequest,
): Promise<OnboardingSaveResponse> {
  return api.post<OnboardingSaveResponse>("/api/onboarding/save", data);
}

export async function uploadResume(
  file: File,
): Promise<ResumeUploadResponse> {
  const { authenticatedFetch } = await import("@/lib/api");

  const formData = new FormData();
  formData.append("file", file);

  const response = await authenticatedFetch("/api/onboarding/upload-resume", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw {
      status: response.status,
      message: response.statusText,
      detail: errorBody.detail ?? JSON.stringify(errorBody),
    };
  }

  return response.json() as Promise<ResumeUploadResponse>;
}
