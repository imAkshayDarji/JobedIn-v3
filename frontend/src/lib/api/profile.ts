import { api } from "@/lib/api";
import type { ProfileMeResponse } from "@/types/profile";

export async function getProfileMe(): Promise<ProfileMeResponse> {
  return api.get<ProfileMeResponse>("/api/profile/me");
}
