import { api } from "@/lib/api";
import type {
  ApplicationDetail,
  ApplicationListResponse,
  ApplicationStats,
  ApplicationStatus,
  ApplicationUpdate,
} from "@/types/application";

interface ListApplicationsParams {
  status?: ApplicationStatus;
  company?: string;
  sortBy?: string;
  limit?: number;
  offset?: number;
}

export async function listApplications(
  params: ListApplicationsParams = {},
): Promise<ApplicationListResponse> {
  const searchParams = new URLSearchParams({
    limit: String(params.limit ?? 100),
    offset: String(params.offset ?? 0),
    sort_by: params.sortBy ?? "created_at",
  });
  if (params.status) searchParams.set("status", params.status);
  if (params.company) searchParams.set("company", params.company);

  return api.get<ApplicationListResponse>(
    `/api/applications?${searchParams.toString()}`,
  );
}

export async function getApplication(
  id: string,
): Promise<ApplicationDetail> {
  return api.get<ApplicationDetail>(`/api/applications/${id}`);
}

export async function updateApplication(
  id: string,
  data: ApplicationUpdate,
): Promise<ApplicationDetail> {
  return api.patch<ApplicationDetail>(`/api/applications/${id}`, data);
}

export async function deleteApplication(id: string): Promise<void> {
  await api.delete(`/api/applications/${id}`);
}

export async function getApplicationStats(): Promise<ApplicationStats> {
  return api.get<ApplicationStats>("/api/applications/stats");
}

export async function updateApplicationNotes(
  id: string,
  notes: string | null,
): Promise<ApplicationDetail> {
  return api.post<ApplicationDetail>(`/api/applications/${id}/notes`, {
    notes,
  });
}
