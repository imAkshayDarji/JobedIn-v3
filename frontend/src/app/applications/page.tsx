"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { PipelineColumn } from "@/components/features/PipelineColumn";
import { ApplicationDetailModal } from "@/components/features/ApplicationDetailModal";
import { BulkApplyModal } from "@/components/features/BulkApplyModal";
import { listApplications, getApplication, getApplicationStats } from "@/lib/api/applications";
import type {
  ApplicationListItem,
  ApplicationDetail,
  ApplicationStats,
  ApplicationStatus,
} from "@/types/application";

const PIPELINE_STATUSES: ApplicationStatus[] = [
  "saved",
  "generating",
  "ready",
  "applying",
  "applied",
  "applied_with_issues",
  "screening",
  "interview",
  "offer",
];

const TERMINAL_STATUSES: ApplicationStatus[] = [
  "manual_required",
  "failed",
  "rejected",
  "withdrawn",
];

type ViewMode = "pipeline" | "list";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationListItem[]>([]);
  const [stats, setStats] = useState<ApplicationStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [companySearch, setCompanySearch] = useState("");
  const [companySearchInput, setCompanySearchInput] = useState("");
  const [statusFilter, setStatusFilter] = useState<ApplicationStatus | "">("");
  const [viewMode, setViewMode] = useState<ViewMode>("pipeline");
  const [selectedApplication, setSelectedApplication] = useState<ApplicationDetail | null>(null);
  const [showTerminal, setShowTerminal] = useState(false);

  const [bulkMode, setBulkMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [showBulkModal, setShowBulkModal] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      setCompanySearch(companySearchInput);
    }, 300);
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [companySearchInput]);

  useEffect(() => {
    loadData();
  }, [companySearch, statusFilter]);

  async function loadData() {
    setLoading(true);
    setError(false);
    try {
      const [appsResponse, statsResponse] = await Promise.all([
        listApplications({
          company: companySearch || undefined,
          status: statusFilter || undefined,
          limit: 200,
        }),
        getApplicationStats(),
      ]);
      setApplications(appsResponse.applications);
      setStats(statsResponse);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }

  async function handleApplicationClick(app: ApplicationListItem) {
    if (bulkMode) {
      toggleSelect(app.id);
      return;
    }
    try {
      const detail = await getApplication(app.id);
      setSelectedApplication(detail);
    } catch {
      // silently fail
    }
  }

  function handleCloseModal() {
    setSelectedApplication(null);
  }

  const handleUpdated = useCallback(() => {
    setSelectedApplication(null);
    loadData();
  }, [companySearch, statusFilter]);

  const handleDeleted = useCallback(() => {
    setSelectedApplication(null);
    loadData();
  }, [companySearch, statusFilter]);

  function getApplicationsByStatus(status: ApplicationStatus): ApplicationListItem[] {
    return applications.filter((a) => a.status === status);
  }

  const readyApps = getApplicationsByStatus("ready");

  function toggleSelect(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        if (next.size >= 10) return prev;
        next.add(id);
      }
      return next;
    });
  }

  function handleSelectAllReady() {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      const readyIds = readyApps.map((a) => a.id);
      const allSelected = readyIds.every((id) => next.has(id));

      if (allSelected) {
        readyIds.forEach((id) => next.delete(id));
      } else {
        const toAdd = readyIds.filter((id) => !next.has(id));
        const available = 10 - next.size;
        toAdd.slice(0, available).forEach((id) => next.add(id));
      }
      return next;
    });
  }

  function handleBulkApply() {
    setShowBulkModal(true);
  }

  const selectedJobs = applications
    .filter((a) => selectedIds.has(a.id))
    .map((a) => ({
      id: a.id,
      title: a.job.title,
      company: a.job.company,
    }));

  return (
    <AppLayout>
      <div className="mx-auto max-w-[1600px] px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Applications</h1>
            <p className="text-sm text-gray-500 mt-1">
              {stats ? `${stats.total} total` : "Loading..."}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setBulkMode(!bulkMode);
                setSelectedIds(new Set());
              }}
              disabled={readyApps.length === 0}
              title={readyApps.length === 0 ? "No ready applications to apply to" : undefined}
              className={`rounded-md px-4 py-2 text-sm font-medium transition-colors ${
                bulkMode
                  ? "bg-orange-600 text-white hover:bg-orange-700"
                  : readyApps.length === 0
                    ? "bg-gray-100 text-gray-400 cursor-not-allowed"
                    : "border border-gray-300 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              {bulkMode ? "Cancel" : "Bulk Apply"}
            </button>
            <Link
              href="/jobs"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
            >
              Discover Jobs
            </Link>
          </div>
        </div>

        {bulkMode && (
          <div className="mb-4 bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={handleSelectAllReady}
                className="text-sm font-medium text-orange-700 hover:text-orange-800 underline"
              >
                Select All Ready ({readyApps.length})
              </button>
              {readyApps.length > 10 && (
                <span className="text-xs text-orange-600">
                  Max 10 at a time
                </span>
              )}
              <span className="text-sm text-orange-700">
                {selectedIds.size} selected
              </span>
            </div>
            <button
              type="button"
              onClick={handleBulkApply}
              disabled={selectedIds.size === 0}
              className="rounded-md bg-orange-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              Apply to Selected ({selectedIds.size})
            </button>
          </div>
        )}

        {stats && stats.total > 0 && (
          <div className="flex flex-wrap gap-2 mb-4">
            {Object.entries(stats.by_status).map(([status, count]) => (
              <button
                key={status}
                type="button"
                onClick={() =>
                  setStatusFilter(statusFilter === status ? "" : (status as ApplicationStatus))
                }
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                  statusFilter === status
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                }`}
              >
                <span className="capitalize">{status.replace(/_/g, " ")}</span>
                <span className="font-semibold">{count}</span>
              </button>
            ))}
          </div>
        )}

        <div className="flex items-center gap-3 mb-6">
          <input
            type="text"
            value={companySearchInput}
            onChange={(e) => setCompanySearchInput(e.target.value)}
            placeholder="Search by company..."
            maxLength={200}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-700 placeholder-gray-400 w-56"
          />
          <div className="flex items-center rounded-md border border-gray-300 overflow-hidden">
            <button
              type="button"
              onClick={() => setViewMode("pipeline")}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                viewMode === "pipeline"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              Pipeline
            </button>
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                viewMode === "list"
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 hover:bg-gray-50"
              }`}
            >
              List
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex gap-4 overflow-x-auto pb-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div
                key={i}
                className="min-w-[280px] max-w-[320px] w-[300px] flex-shrink-0"
              >
                <div className="animate-pulse rounded-lg border-t-4 border-t-gray-200 bg-gray-50">
                  <div className="px-3 py-2.5 border-b border-gray-200">
                    <div className="h-4 bg-gray-200 rounded w-1/2" />
                  </div>
                  <div className="p-2 space-y-2">
                    {Array.from({ length: 2 }).map((_, j) => (
                      <div
                        key={j}
                        className="animate-pulse rounded-lg border border-gray-200 bg-white p-4"
                      >
                        <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                        <div className="h-3 bg-gray-200 rounded w-1/2" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">Failed to load applications.</p>
            <button
              onClick={() => loadData()}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        ) : applications.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">No applications yet.</p>
            <Link
              href="/jobs"
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Discover Jobs
            </Link>
            <p className="text-sm text-gray-400 mt-2">
              Save jobs to start tracking your applications.
            </p>
          </div>
        ) : bulkMode && readyApps.length === 0 ? (
          <div className="text-center py-16">
            <p className="text-gray-500">No ready applications to apply to.</p>
            <p className="text-sm text-gray-400 mt-2">
              Applications need to be in &quot;ready&quot; status before you can auto-apply.
            </p>
          </div>
        ) : viewMode === "pipeline" ? (
          <>
            <div className="flex gap-4 overflow-x-auto pb-4">
              {PIPELINE_STATUSES.map((status) => (
                <PipelineColumn
                  key={status}
                  status={status}
                  applications={getApplicationsByStatus(status)}
                  onApplicationClick={handleApplicationClick}
                  selectable={bulkMode && status === "ready"}
                  selectedIds={selectedIds}
                  onSelect={toggleSelect}
                />
              ))}
            </div>

            {TERMINAL_STATUSES.some(
              (s) => getApplicationsByStatus(s).length > 0,
            ) && (
              <div className="mt-6">
                <button
                  type="button"
                  onClick={() => setShowTerminal(!showTerminal)}
                  className="text-sm text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {showTerminal ? "Hide" : "Show"} Terminal (
                  {TERMINAL_STATUSES.reduce(
                    (sum, s) => sum + getApplicationsByStatus(s).length,
                    0,
                  )}
                  )
                </button>
                {showTerminal && (
                  <div className="flex gap-4 overflow-x-auto pb-4 mt-3">
                    {TERMINAL_STATUSES.map((status) => (
                      <PipelineColumn
                        key={status}
                        status={status}
                        applications={getApplicationsByStatus(status)}
                        onApplicationClick={handleApplicationClick}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {applications.map((app) => (
              <div key={app.id}>
                <button
                  type="button"
                  onClick={() => handleApplicationClick(app)}
                  className="w-full text-left"
                >
                  <div className="rounded-lg border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm transition-all">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="font-semibold text-gray-900 text-sm truncate">
                        {app.job.title}
                      </h3>
                      <span className="text-xs text-gray-500 capitalize ml-2 flex-shrink-0">
                        {app.status.replace(/_/g, " ")}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600">{app.job.company}</p>
                    {app.job.location && (
                      <p className="text-xs text-gray-500 mt-0.5">
                        {app.job.location}
                      </p>
                    )}
                    {app.match_score != null && (
                      <p className="text-xs text-gray-400 mt-1">
                        Match: {Math.round(app.match_score)}%
                      </p>
                    )}
                  </div>
                </button>
              </div>
            ))}
          </div>
        )}

        {selectedApplication && (
          <ApplicationDetailModal
            application={selectedApplication}
            onClose={handleCloseModal}
            onUpdated={handleUpdated}
            onDeleted={handleDeleted}
          />
        )}

        {showBulkModal && selectedJobs.length > 0 && (
          <BulkApplyModal
            applicationIds={Array.from(selectedIds)}
            jobs={selectedJobs}
            onClose={() => {
              setShowBulkModal(false);
              setBulkMode(false);
              setSelectedIds(new Set());
            }}
            onCompleted={() => {
              loadData();
            }}
          />
        )}
      </div>
    </AppLayout>
  );
}
