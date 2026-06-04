import { api, authenticatedFetch } from "@/lib/api";

export interface UserResumeMetadata {
  has_uploaded_resume: boolean;
  filename: string | null;
  uploaded_at: string | null;
  text_preview: string | null;
}

export interface UserResumeUploadResponse {
  has_uploaded_resume: boolean;
  filename: string;
  uploaded_at: string;
  text_preview: string | null;
}

export async function getUserResume(): Promise<UserResumeMetadata> {
  return api.get<UserResumeMetadata>("/api/user/resume");
}

export async function uploadUserResume(file: File): Promise<UserResumeUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await authenticatedFetch("/api/user/resume", {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw {
      status: response.status,
      detail: (body as { detail?: string }).detail ?? response.statusText,
    };
  }
  return response.json() as Promise<UserResumeUploadResponse>;
}

export async function deleteUserResume(): Promise<void> {
  await api.delete("/api/user/resume");
}
