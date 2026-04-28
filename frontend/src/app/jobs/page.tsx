"use client";

import { useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { JobCard } from "@/components/features/JobCard";
import { listJobs, matchJobs, getMatchStatus, discoverJobs, getDiscoverStatus } from "@/lib/api/jobs";
import type { JobListItem } from "@/types/job";

type SortOption = "match_score" | "created_at" | "salary_max";

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<SortOption>("match_score");
  const [source, setSource] = useState<string>("");
  const [matchStatus, setMatchStatus] = useState<string | null>(null);
  const [matchTaskId, setMatchTaskId] = useState<string | null>(null);
  const [discoverStatus, setDiscoverStatus] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
  }, [sortBy, source]);

  async function loadJobs() {
    try {
      const response = await listJobs(20, 0, sortBy, source || undefined);
      setJobs(response.jobs);
      setTotal(response.total);
    } catch {
      setJobs([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }

  async function handleMatchJobs() {
    try {
      const response = await matchJobs();
      setMatchTaskId(response.task_id);
      setMatchStatus("pending");
      pollMatchStatus(response.task_id);
    } catch {
      setMatchStatus(null);
    }
  }

  async function pollMatchStatus(taskId: string) {
    const interval = setInterval(async () => {
      try {
        const status = await getMatchStatus(taskId);
        setMatchStatus(status.status);
        if (status.status === "completed" || status.status === "failed" || status.status === "unknown") {
          clearInterval(interval);
          if (status.status === "completed") {
            loadJobs();
          }
        }
      } catch {
        clearInterval(interval);
        setMatchStatus(null);
      }
    }, 2000);
  }

  async function handleDiscover() {
    try {
      const response = await discoverJobs({ sources: ["jsearch", "adzuna", "remotive", "reed"] });
      setDiscoverStatus("pending");
      pollDiscoverStatus(response.job_id);
    } catch {
      setDiscoverStatus(null);
    }
  }

  async function pollDiscoverStatus(jobId: string) {
    const interval = setInterval(async () => {
      try {
        const status = await getDiscoverStatus(jobId);
        if (status.status === "completed" || status.status === "failed" || status.status === "unknown") {
          clearInterval(interval);
          setDiscoverStatus(status.status === "completed" ? "completed" : null);
          if (status.status === "completed") {
            handleMatchJobs();
            loadJobs();
          }
        }
      } catch {
        clearInterval(interval);
        setDiscoverStatus(null);
      }
    }, 3000);
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
            <p className="text-sm text-gray-500 mt-1">
              {total} {total === 1 ? "job" : "jobs"} found
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleMatchJobs}
              disabled={matchStatus === "pending" || matchStatus === "in_progress"}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {matchStatus === "pending" || matchStatus === "in_progress" ? "Matching..." : "Score Jobs"}
            </button>
            <button
              onClick={handleDiscover}
              disabled={discoverStatus === "pending"}
              className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {discoverStatus === "pending" ? "Discovering..." : "Discover Jobs"}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 mb-6">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortOption)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="match_score">Sort by Match Score</option>
            <option value="created_at">Sort by Newest</option>
            <option value="salary_max">Sort by Salary</option>
          </select>

          <select
            value={source}
            onChange={(e) => setSource(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All Sources</option>
            <option value="linkedin">LinkedIn</option>
            <option value="jsearch">JSearch</option>
            <option value="adzuna">Adzuna</option>
            <option value="remotive">Remotive</option>
            <option value="reed">Reed</option>
          </select>
        </div>

        {loading ? (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="animate-pulse rounded-lg border border-gray-200 bg-white p-5">
                <div className="h-4 bg-gray-200 rounded w-1/4 mb-2" />
                <div className="h-5 bg-gray-200 rounded w-3/4 mb-1" />
                <div className="h-4 bg-gray-200 rounded w-1/2" />
              </div>
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">No jobs found.</p>
            <button
              onClick={handleDiscover}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Discover Jobs
            </button>
            <p className="text-sm text-gray-400 mt-2">
              Discover jobs to get started.
            </p>
          </div>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {jobs.map((job) => (
              <JobCard key={job.id} job={job} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
