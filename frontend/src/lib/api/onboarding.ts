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
  const supabase = await import("@/lib/supabase/client").then(
    (m) => m.createClient,
  );
  const client = supabase();
  const {
    data: { session },
  } = await client.auth.getSession();

  const formData = new FormData();
  formData.append("file", file);

  const baseUrl =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  const response = await fetch(`${baseUrl}/api/onboarding/upload-resume`, {
    method: "POST",
    headers: {
      ...(session?.access_token
        ? { Authorization: `Bearer ${session.access_token}` }
        : {}),
    },
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
