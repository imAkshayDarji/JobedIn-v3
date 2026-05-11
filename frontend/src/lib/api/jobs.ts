import { api } from "@/lib/api";
import type {
  DiscoverRequest,
  DiscoverResponse,
  DiscoverStatusResponse,
  JobDetail,
  JobListResponse,
  JobMatchScore,
  MatchStatus,
  SavedJobsResponse,
  SourcesStatusResponse,
} from "@/types/job";

export async function listJobs(
  limit: number = 20,
  offset: number = 0,
  sortBy: string = "created_at",
  source?: string,
  experienceLevel?: string,
  search?: string,
  jobType?: string,
  remotePolicy?: string,
): Promise<JobListResponse> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
    sort_by: sortBy,
  });
  if (source) params.set("source", source);
  if (experienceLevel) params.set("experience_level", experienceLevel);
  if (search) params.set("search", search);
  if (jobType) params.set("job_type", jobType);
  if (remotePolicy) params.set("remote_policy", remotePolicy);
  return api.get<JobListResponse>(`/api/jobs?${params.toString()}`);
}

export async function getJob(id: string): Promise<JobDetail> {
  return api.get<JobDetail>(`/api/jobs/${id}`);
}

export async function getJobScore(id: string): Promise<JobMatchScore> {
  return api.get<JobMatchScore>(`/api/jobs/${id}/score`);
}

export async function matchJobs(): Promise<{ task_id: string; message: string }> {
  return api.post<{ task_id: string; message: string }>("/api/jobs/match", {});
}

export async function getMatchStatus(taskId?: string): Promise<MatchStatus> {
  const params = taskId ? `?task_id=${taskId}` : "";
  return api.get<MatchStatus>(`/api/jobs/match/status${params}`);
}

export async function discoverJobs(
  data: DiscoverRequest,
): Promise<DiscoverResponse> {
  return api.post<DiscoverResponse>("/api/jobs/discover", data);
}

export async function getDiscoverStatus(
  jobId?: string,
): Promise<DiscoverStatusResponse> {
  const params = jobId ? `?job_id=${jobId}` : "";
  return api.get<DiscoverStatusResponse>(`/api/jobs/discover/status${params}`);
}

export async function getSourcesStatus(): Promise<SourcesStatusResponse> {
  return api.get<SourcesStatusResponse>("/api/jobs/sources/status");
}

export async function listSavedJobs(
  limit: number = 20,
  offset: number = 0,
): Promise<SavedJobsResponse> {
  return api.get<SavedJobsResponse>(
    `/api/jobs/saved?limit=${limit}&offset=${offset}`,
  );
}

export async function saveJob(jobId: string): Promise<{ message: string; application_id?: string }> {
  return api.post<{ message: string; application_id?: string }>(`/api/jobs/${jobId}/save`, {});
}

export async function unsaveJob(jobId: string): Promise<void> {
  await api.delete(`/api/jobs/${jobId}/save`);
}
