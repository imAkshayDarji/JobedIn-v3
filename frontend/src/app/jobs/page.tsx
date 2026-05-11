"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { JobCard } from "@/components/features/JobCard";
import { ApplyModal } from "@/components/features/ApplyModal";
import { BulkActionToolbar } from "@/components/features/BulkActionToolbar";
import {
  listJobs,
  matchJobs,
  getMatchStatus,
  discoverJobs,
  getDiscoverStatus,
  getSourcesStatus,
  saveJob,
  unsaveJob,
} from "@/lib/api/jobs";
import type { JobListItem, SourceStatus } from "@/types/job";

type SortOption = "match_score" | "created_at" | "salary_max";

/** Boards sent to POST /discover (aligned with backend DISABLED_API_SOURCES; Remotive omitted). */
const DISCOVER_API_SOURCES: readonly string[] = ["jsearch", "adzuna", "reed"];

export default function JobsPage() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("match_score");
  const [source, setSource] = useState<string>("");
  const [experienceLevel, setExperienceLevel] = useState<string>("");
  const [jobType, setJobType] = useState<string>("");
  const [remotePolicy, setRemotePolicy] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [searchInput, setSearchInput] = useState<string>("");
  const [offset, setOffset] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [matchStatus, setMatchStatus] = useState<string | null>(null);
  const [matchTaskId, setMatchTaskId] = useState<string | null>(null);
  const [discoverStatus, setDiscoverStatus] = useState<string | null>(null);
  const [sourceStatuses, setSourceStatuses] = useState<SourceStatus[]>([]);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [applyModalApplicationId, setApplyModalApplicationId] = useState<string | null>(null);
  const [applyModalJobTitle, setApplyModalJobTitle] = useState("");
  const [applyModalCompany, setApplyModalCompany] = useState("");
  const [applyingId, setApplyingId] = useState<string | null>(null);

  const matchIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const discoverIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const PAGE_SIZE = 20;

  useEffect(() => {
    loadSourcesStatus();
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setSearch(searchInput);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [searchInput]);

  useEffect(() => {
    setOffset(0);
    loadJobs(true);
  }, [sortBy, source, experienceLevel, jobType, remotePolicy, search]);

  useEffect(() => {
    if (offset > 0) {
      loadJobs(false);
    }
  }, [offset]);

  useEffect(() => {
    return () => {
      if (matchIntervalRef.current) clearInterval(matchIntervalRef.current);
      if (discoverIntervalRef.current) clearInterval(discoverIntervalRef.current);
    };
  }, []);

  async function loadSourcesStatus() {
    try {
      const response = await getSourcesStatus();
      setSourceStatuses(response.sources);
    } catch {
      // Fail silently
    }
  }

  async function loadJobs(reset: boolean) {
    if (abortRef.current) {
      abortRef.current.abort();
    }
    const controller = new AbortController();
    abortRef.current = controller;

    if (reset) {
      setLoading(true);
    } else {
      setLoadingMore(true);
    }
    setError(false);
    setErrorMessage("");

    try {
      const currentOffset = reset ? 0 : offset;
      const response = await listJobs(
        PAGE_SIZE,
        currentOffset,
        sortBy,
        source || undefined,
        experienceLevel || undefined,
        search || undefined,
        jobType || undefined,
        remotePolicy || undefined,
      );
      if (controller.signal.aborted) return;

      if (reset) {
        setJobs(response.jobs);
      } else {
        setJobs((prev) => [...prev, ...response.jobs]);
      }
      setTotal(response.total);
    } catch {
      if (controller.signal.aborted) return;
      setError(true);
      setErrorMessage("Failed to load jobs. Please try again.");
      if (reset) {
        setJobs([]);
        setTotal(0);
      }
    } finally {
      if (!controller.signal.aborted) {
        setLoading(false);
        setLoadingMore(false);
      }
    }
  }

  function handleLoadMore() {
    setOffset((prev) => prev + PAGE_SIZE);
  }

  const handleRetry = useCallback(() => {
    loadJobs(true);
  }, [sortBy, source, experienceLevel, jobType, remotePolicy, search]);

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

  function pollMatchStatus(taskId: string) {
    if (matchIntervalRef.current) clearInterval(matchIntervalRef.current);
    matchIntervalRef.current = setInterval(async () => {
      try {
        const status = await getMatchStatus(taskId);
        setMatchStatus(status.status);
        if (status.status === "completed" || status.status === "failed" || status.status === "unknown") {
          if (matchIntervalRef.current) clearInterval(matchIntervalRef.current);
          matchIntervalRef.current = null;
          if (status.status === "completed") {
            loadJobs(true);
          }
        }
      } catch {
        if (matchIntervalRef.current) clearInterval(matchIntervalRef.current);
        matchIntervalRef.current = null;
        setMatchStatus(null);
      }
    }, 2000);
  }

  async function handleDiscover() {
    try {
      setError(false);
      setErrorMessage("");
      const response = await discoverJobs({ sources: [...DISCOVER_API_SOURCES] });
      setDiscoverStatus("pending");
      pollDiscoverStatus(response.job_id);
    } catch {
      setDiscoverStatus(null);
      setError(true);
      setErrorMessage("Failed to start job discovery. Please try again.");
    }
  }

  function pollDiscoverStatus(jobId: string) {
    if (discoverIntervalRef.current) clearInterval(discoverIntervalRef.current);
    discoverIntervalRef.current = setInterval(async () => {
      try {
        const status = await getDiscoverStatus(jobId);
        if (status.status === "completed" || status.status === "failed" || status.status === "unknown") {
          if (discoverIntervalRef.current) clearInterval(discoverIntervalRef.current);
          discoverIntervalRef.current = null;
          const succeeded = status.status === "completed" || status.status === "unknown";
          setDiscoverStatus(succeeded ? "completed" : null);
          if (succeeded) {
            handleMatchJobs();
            loadJobs(true);
          }
        }
      } catch {
        if (discoverIntervalRef.current) clearInterval(discoverIntervalRef.current);
        discoverIntervalRef.current = null;
        setDiscoverStatus(null);
      }
    }, 3000);
  }

  function toggleSelect(jobId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(jobId)) {
        next.delete(jobId);
      } else {
        next.add(jobId);
      }
      return next;
    });
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  async function handleSaveFromCard(jobId: string) {
    const job = jobs.find((j) => j.id === jobId);
    if (!job) return;

    if (job.is_saved) {
      try {
        await unsaveJob(jobId);
      } catch {
        // ignore
      }
    } else {
      try {
        await saveJob(jobId);
      } catch {
        // ignore
      }
    }
    loadJobs(true);
  }

  async function handleApplyFromCard(jobId: string) {
    const job = jobs.find((j) => j.id === jobId);
    if (!job) return;

    setApplyingId(jobId);

    let applicationId = job.application_id;

    if (!applicationId) {
      try {
        const result = await saveJob(jobId);
        applicationId = result.application_id ?? null;
      } catch {
        // Ignore — will fail gracefully below
      }
    }

    if (!applicationId) {
      setApplyingId(null);
      return;
    }

    setApplyModalApplicationId(applicationId);
    setApplyModalJobTitle(job.title);
    setApplyModalCompany(job.company);
    setApplyingId(null);
  }

  const linkedinStatus = sourceStatuses.find((s) => s.name === "linkedin");
  const remaining = total - jobs.length;
  const isMatchBusy = matchStatus === "pending" || matchStatus === "in_progress";
  const showBulkToolbar = selectedIds.size >= 2;

  return (
    <AppLayout>
      <div className={`mx-auto max-w-7xl px-6 py-8 ${showBulkToolbar ? "pb-24" : ""}`}>
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
              disabled={isMatchBusy}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isMatchBusy ? "Matching..." : "Score Jobs"}
            </button>
            <div className="flex flex-col items-end">
              <button
                onClick={handleDiscover}
                disabled={discoverStatus === "pending"}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {discoverStatus === "pending" ? "Discovering..." : "Discover Jobs"}
              </button>
              {linkedinStatus && !linkedinStatus.available && (
                <span className="text-[11px] text-gray-400 mt-1">
                  LinkedIn: credentials required
                </span>
              )}
              {linkedinStatus && linkedinStatus.available && (
                <span className="text-[11px] text-green-500 mt-1">
                  LinkedIn: ready
                </span>
              )}
            </div>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-md bg-red-50 border border-red-200 p-4 flex items-center justify-between">
            <p className="text-sm text-red-700">{errorMessage}</p>
            <button
              onClick={handleRetry}
              className="rounded-md bg-red-100 px-3 py-1 text-sm font-medium text-red-700 hover:bg-red-200"
            >
              Retry
            </button>
          </div>
        )}

        <div className="flex flex-wrap items-center gap-3 mb-6">
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search jobs..."
            maxLength={200}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 placeholder-gray-400 w-56"
          />

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
            <option value="reed">Reed</option>
          </select>

          <select
            value={experienceLevel}
            onChange={(e) => setExperienceLevel(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All Experience</option>
            <option value="student">Student</option>
            <option value="fresher">Fresher</option>
            <option value="junior">Junior</option>
            <option value="mid">Mid</option>
            <option value="senior">Senior</option>
            <option value="lead">Lead</option>
            <option value="executive">Executive</option>
          </select>

          <select
            value={jobType}
            onChange={(e) => setJobType(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All Job Types</option>
            <option value="full-time">Full-time</option>
            <option value="part-time">Part-time</option>
            <option value="contract">Contract</option>
            <option value="internship">Internship</option>
          </select>

          <select
            value={remotePolicy}
            onChange={(e) => setRemotePolicy(e.target.value)}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700"
          >
            <option value="">All Remote Policies</option>
            <option value="remote">Remote</option>
            <option value="hybrid">Hybrid</option>
            <option value="onsite">On-site</option>
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
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {jobs.map((job) => (
                <JobCard
                  key={job.id}
                  job={job}
                  isSaved={job.is_saved}
                  selected={selectedIds.has(job.id)}
                  onToggleSelect={toggleSelect}
                  onSave={handleSaveFromCard}
                  onApply={handleApplyFromCard}
                />
              ))}
            </div>
            {remaining > 0 && (
              <div className="mt-6 text-center">
                <button
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className="rounded-md border border-gray-300 bg-white px-6 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loadingMore ? "Loading..." : `Load More (${remaining} remaining)`}
                </button>
              </div>
            )}
          </>
        )}
      </div>

      {showBulkToolbar && (
        <BulkActionToolbar
          selectedJobIds={Array.from(selectedIds)}
          onClearSelection={clearSelection}
          onActionComplete={() => {
            clearSelection();
            loadJobs(true);
          }}
        />
      )}

      {applyModalApplicationId && (
        <ApplyModal
          applicationId={applyModalApplicationId}
          jobTitle={applyModalJobTitle}
          companyName={applyModalCompany}
          onClose={() => {
            setApplyModalApplicationId(null);
            setApplyModalJobTitle("");
            setApplyModalCompany("");
          }}
          onCompleted={() => {
            setApplyModalApplicationId(null);
            setApplyModalJobTitle("");
            setApplyModalCompany("");
            loadJobs(true);
          }}
        />
      )}
    </AppLayout>
  );
}
