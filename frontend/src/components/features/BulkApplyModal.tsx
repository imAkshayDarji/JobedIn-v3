"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  X,
  CheckCircle2,
  XCircle,
  ExternalLink,
  Loader2,
  AlertTriangle,
} from "lucide-react";
import { applyBulk, getBulkApplyStatus } from "@/lib/api/apply";
import type { ApplyBulkStatusResponse } from "@/types/apply";

interface BulkJobInfo {
  id: string;
  title: string;
  company: string;
}

interface BulkApplyModalProps {
  applicationIds: string[];
  jobs: BulkJobInfo[];
  onClose: () => void;
  onCompleted: () => void;
}

type BulkPhase = "confirm" | "applying" | "done";

export function BulkApplyModal({
  applicationIds,
  jobs,
  onClose,
  onCompleted,
}: BulkApplyModalProps) {
  const [phase, setPhase] = useState<BulkPhase>("confirm");
  const [progress, setProgress] = useState<ApplyBulkStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const [isBackground, setIsBackground] = useState(false);
  const [showToast, setShowToast] = useState(false);

  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, []);

  const startPolling = useCallback(
    (taskId: string) => {
      if (pollingRef.current) clearInterval(pollingRef.current);

      const poll = async () => {
        try {
          const status = await getBulkApplyStatus(taskId);
          if (!mountedRef.current) return;

          setProgress(status);

          if (status.pending === 0) {
            if (pollingRef.current) clearInterval(pollingRef.current);
            setPhase("done");

            if (isBackground) {
              setShowToast(true);
              setTimeout(() => {
                if (mountedRef.current) setShowToast(false);
              }, 5000);
            }
          }
        } catch (err: unknown) {
          const status = (err as { status?: number })?.status;
          if (status === 404) {
            if (pollingRef.current) clearInterval(pollingRef.current);
            setError("This apply session has expired. Please try again.");
            setPhase("done");
          }
        }
      };

      poll();
      pollingRef.current = setInterval(poll, 2000);
    },
    [isBackground],
  );

  async function handleStartApply() {
    setIsStarting(true);
    setError(null);

    try {
      const response = await applyBulk(applicationIds);
      setPhase("applying");
      startPolling(response.bulk_task_id);
    } catch (err: unknown) {
      const status = (err as { status?: number })?.status;
      const message = (err as { message?: string })?.message ?? "Failed to start bulk apply";

      if (status === 409) {
        setError(message);
      } else {
        setError(message);
      }
    } finally {
      setIsStarting(false);
    }
  }

  function handleBackgroundClose() {
    setIsBackground(true);
    onClose();
  }

  const completedCount = progress ? progress.completed : 0;
  const failedCount = progress ? progress.failed : 0;
  const manualCount = progress ? progress.manual_required : 0;
  const total = progress?.total ?? applicationIds.length;
  const processedCount = completedCount + failedCount + manualCount;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center sm:items-center">
      <div className="fixed inset-0 bg-black/50" onClick={phase === "confirm" ? onClose : undefined} />
      <div className="relative bg-white rounded-xl shadow-xl w-full sm:max-w-lg mx-0 sm:mx-4 max-h-[90vh] overflow-y-auto sm:rounded-xl rounded-none min-h-screen sm:min-h-0">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl z-10">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Bulk Apply</h2>
            <p className="text-sm text-gray-500">
              {phase === "confirm"
                ? `${applicationIds.length} job${applicationIds.length !== 1 ? "s" : ""} selected`
                : phase === "applying"
                  ? `${processedCount} of ${total} processed`
                  : "Complete"}
            </p>
          </div>
          <button
            type="button"
            onClick={phase === "confirm" ? onClose : handleBackgroundClose}
            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {phase === "confirm" && (
            <>
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {jobs.map((job) => (
                  <div
                    key={job.id}
                    className="flex items-center gap-3 rounded-lg border border-gray-100 bg-gray-50 px-3 py-2"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900 truncate">{job.title}</p>
                      <p className="text-xs text-gray-500">{job.company}</p>
                    </div>
                  </div>
                ))}
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                  <p className="text-sm text-red-800">{error}</p>
                </div>
              )}

              <button
                type="button"
                onClick={handleStartApply}
                disabled={isStarting}
                className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 transition-colors"
              >
                {isStarting ? "Starting..." : `Apply to All (${applicationIds.length})`}
              </button>
            </>
          )}

          {phase === "applying" && progress && (
            <>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-600">
                    {progress.pending > 0
                      ? `${progress.pending} in queue, processing...`
                      : "Finalizing..."}
                  </span>
                  <span className="font-medium text-gray-900">
                    {processedCount}/{total}
                  </span>
                </div>

                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${total > 0 ? (processedCount / total) * 100 : 0}%`,
                    }}
                  />
                </div>
              </div>

              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {progress.results.map((r) => {
                  const job = jobs.find((j) => j.id === r.application_id);
                  const isComplete = r.status === "applied";
                  const isFailed = r.status === "failed";
                  const isManual = r.status === "manual_required";
                  const isPending = !isComplete && !isFailed && !isManual;

                  return (
                    <div
                      key={r.application_id}
                      className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2"
                    >
                      <div className="flex items-center gap-2 min-w-0">
                        {isComplete && <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />}
                        {isFailed && <XCircle className="w-4 h-4 text-red-500 flex-shrink-0" />}
                        {isManual && <AlertTriangle className="w-4 h-4 text-amber-500 flex-shrink-0" />}
                        {isPending && <Loader2 className="w-4 h-4 text-gray-400 animate-spin flex-shrink-0" />}
                        <span className="text-sm text-gray-700 truncate">
                          {job?.title ?? r.application_id}
                        </span>
                      </div>
                      {isManual && r.manual_url && (
                        <a
                          href={r.manual_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="flex-shrink-0 text-xs text-amber-600 hover:underline ml-2"
                        >
                          Apply
                        </a>
                      )}
                    </div>
                  );
                })}
              </div>

              <button
                type="button"
                onClick={handleBackgroundClose}
                className="text-sm text-gray-500 hover:text-gray-700"
              >
                Continue in background
              </button>
            </>
          )}

          {phase === "done" && progress && (
            <>
              <div className="space-y-3">
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="rounded-lg bg-green-50 p-3">
                    <p className="text-2xl font-bold text-green-600">{progress.completed}</p>
                    <p className="text-xs text-green-700">Succeeded</p>
                  </div>
                  <div className="rounded-lg bg-red-50 p-3">
                    <p className="text-2xl font-bold text-red-600">{progress.failed}</p>
                    <p className="text-xs text-red-700">Failed</p>
                  </div>
                  <div className="rounded-lg bg-amber-50 p-3">
                    <p className="text-2xl font-bold text-amber-600">{progress.manual_required}</p>
                    <p className="text-xs text-amber-700">Manual</p>
                  </div>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <p className="text-sm text-red-800">{error}</p>
                  </div>
                )}

                {progress.results.filter((r) => r.status === "manual_required").length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-amber-700 uppercase tracking-wider">
                      Needs Manual Action
                    </p>
                    {progress.results
                      .filter((r) => r.status === "manual_required")
                      .map((r) => {
                        const job = jobs.find((j) => j.id === r.application_id);
                        return (
                          <div
                            key={r.application_id}
                            className="flex items-center justify-between rounded-lg border border-amber-200 bg-amber-50 px-3 py-2"
                          >
                            <span className="text-sm text-amber-800 truncate">
                              {job?.title ?? r.application_id}
                            </span>
                            <a
                              href={r.manual_url ?? "#"}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex-shrink-0 inline-flex items-center gap-1 rounded-md bg-amber-600 px-2 py-1 text-xs font-medium text-white hover:bg-amber-700 ml-2"
                            >
                              <ExternalLink className="w-3 h-3" />
                              Apply
                            </a>
                          </div>
                        );
                      })}
                  </div>
                )}

                <button
                  type="button"
                  onClick={() => {
                    onCompleted();
                    onClose();
                  }}
                  className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
                >
                  Done
                </button>
              </div>
            </>
          )}
        </div>
      </div>

      {showToast && (
        <div className="fixed bottom-6 right-6 z-[70] max-w-sm">
          <div className="bg-gray-900 text-white rounded-lg shadow-lg px-4 py-3 flex items-center gap-3">
            <CheckCircle2 className="w-5 h-5 text-green-400 flex-shrink-0" />
            <div className="text-sm">
              <p className="font-medium">Bulk Apply Complete</p>
              <p className="text-gray-300 text-xs">
                {progress?.completed ?? 0} succeeded, {progress?.failed ?? 0} failed,{" "}
                {progress?.manual_required ?? 0} need manual action.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowToast(false)}
              className="text-gray-400 hover:text-white ml-2"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
