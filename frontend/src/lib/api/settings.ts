import { api } from "@/lib/api";

interface LinkedInStatus {
  has_credentials: boolean;
  email: string | null;
  last_scraped_at: string | null;
}

export async function saveLinkedInCredentials(
  email: string,
  password: string,
): Promise<{ message: string }> {
  return api.post<{ message: string }>("/api/settings/linkedin-credentials", {
    email,
    password,
  });
}

export async function getLinkedInStatus(): Promise<LinkedInStatus> {
  return api.get<LinkedInStatus>("/api/settings/linkedin-status");
}

export async function deleteLinkedInCredentials(): Promise<{
  message: string;
}> {
  return api.delete<{ message: string }>("/api/settings/linkedin-credentials");
}
