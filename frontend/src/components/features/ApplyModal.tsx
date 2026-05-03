"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  X,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  ExternalLink,
  RotateCcw,
  Camera,
} from "lucide-react";
import { ApplyStepProgress } from "./ApplyStepProgress";
import { applySingle, connectApplyStream } from "@/lib/api/apply";
import type { ApplySSEEvent } from "@/types/apply";

interface ApplyModalProps {
  applicationId: string;
  jobTitle: string;
  companyName: string;
  initialStatus?: string;
  onClose: () => void;
  onCompleted: () => void;
}

type ApplyResult =
  | { type: "success" }
  | { type: "issues"; screenshotPath: string | null }
  | { type: "manual"; manualUrl: string | null }
  | { type: "failed"; error: string };

export function ApplyModal({
  applicationId,
  jobTitle,
  companyName,
  initialStatus,
  onClose,
  onCompleted,
}: ApplyModalProps) {
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(new Set());
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [result, setResult] = useState<ApplyResult | null>(null);
  const [isApplying, setIsApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showCloseConfirm, setShowCloseConfirm] = useState(false);
  const [showScreenshot, setShowScreenshot] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [started, setStarted] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      abortRef.current?.abort();
    };
  }, []);

  const handleEvent = useCallback((event: ApplySSEEvent) => {
    if (!mountedRef.current) return;

    if (event.event === "step_completed" && event.step) {
      setCompletedSteps((prev) => {
        const next = new Set(prev);
        next.add(event.step!);
        return next;
      });
      setCurrentStep(null);
    }

    if (event.event === "status_changed" && event.step) {
      setCurrentStep(event.step);
    }

    if (event.event === "done" || (event.event === "status_changed" && event.status)) {
      const status = event.status;
      if (status === "applied") {
        setResult({ type: "success" });
      } else if (status === "applied_with_issues") {
        setResult({ type: "issues", screenshotPath: null });
      } else if (status === "manual_required") {
        setResult({ type: "manual", manualUrl: null });
      } else if (status === "failed") {
        setResult({ type: "failed", error: event.error ?? "Application failed" });
      }
      setIsApplying(false);
      setCurrentStep(null);
    }
  }, []);

  const handleDone = useCallback(() => {
    if (!mountedRef.current) return;
    setIsApplying(false);
    onCompleted();
  }, [onCompleted]);

  const handleError = useCallback((err: Error) => {
    if (!mountedRef.current) return;
    setError(err.message);
    setIsApplying(false);
  }, []);

  const startApply = useCallback(
    async (isResume: boolean) => {
      setIsApplying(true);
      setError(null);
      setResult(null);
      setCompletedSteps(new Set());
      setCurrentStep(null);
      setStarted(true);

      try {
        if (!isResume) {
          await applySingle(applicationId);
        }
      } catch (err: unknown) {
        const message =
          (err as { message?: string })?.message ?? "Failed to start application";
        setError(message);
        setIsApplying(false);
        return;
      }

      abortRef.current?.abort();
      abortRef.current = connectApplyStream(applicationId, {
        onEvent: handleEvent,
        onDone: handleDone,
        onError: handleError,
      });
    },
    [applicationId, handleEvent, handleDone, handleError],
  );

  useEffect(() => {
    if (started) return;

    if (initialStatus === "applying") {
      startApply(true);
    }
  }, [initialStatus, started, startApply]);

  function handleClose() {
    if (isApplying && !showCloseConfirm) {
      setShowCloseConfirm(true);
      return;
    }
    abortRef.current?.abort();
    onClose();
  }

  function handleRetry() {
    setRetryCount((c) => c + 1);
    abortRef.current?.abort();
    startApply(false);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center sm:items-center">
      <div className="fixed inset-0 bg-black/50" onClick={handleClose} />
      <div className="relative bg-white rounded-xl shadow-xl w-full sm:max-w-md mx-0 sm:mx-4 max-h-[90vh] overflow-y-auto sm:rounded-xl rounded-none min-h-screen sm:min-h-0">
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between rounded-t-xl z-10">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">Auto Apply</h2>
            <p className="text-sm text-gray-500">
              {jobTitle} &middot; {companyName}
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="rounded-lg p-1.5 hover:bg-gray-100 transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="px-6 py-5 space-y-5">
          {showCloseConfirm && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <p className="text-sm text-amber-800 mb-3">
                The application will continue in the background. You can check its status on the
                Applications page.
              </p>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    abortRef.current?.abort();
                    onClose();
                  }}
                  className="rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
                >
                  Close Anyway
                </button>
                <button
                  type="button"
                  onClick={() => setShowCloseConfirm(false)}
                  className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-50"
                >
                  Keep Watching
                </button>
              </div>
            </div>
          )}

          {!started && !result && !error && (
            <div className="text-center py-8">
              <p className="text-gray-600 mb-4">
                Ready to auto-apply to <strong>{jobTitle}</strong> at{" "}
                <strong>{companyName}</strong>?
              </p>
              <button
                type="button"
                onClick={() => startApply(false)}
                className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
              >
                Start Auto Apply
              </button>
            </div>
          )}

          {(isApplying || result || error) && (
            <ApplyStepProgress completedSteps={completedSteps} currentStep={currentStep} />
          )}

          {error && !result && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-red-800 font-medium">Error</p>
                  <p className="text-sm text-red-700 mt-1">{error}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                <RotateCcw className="w-3 h-3" />
                Retry
              </button>
            </div>
          )}

          {result?.type === "success" && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                <div>
                  <p className="text-sm text-green-800 font-medium">
                    Application submitted successfully
                  </p>
                  <p className="text-xs text-green-700 mt-1">
                    Your application has been submitted to {companyName}.
                  </p>
                </div>
              </div>
            </div>
          )}

          {result?.type === "issues" && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                <div>
                  <p className="text-sm text-yellow-800 font-medium">Applied with issues</p>
                  <p className="text-xs text-yellow-700 mt-1">
                    The application was submitted but some steps had issues.
                  </p>
                </div>
              </div>
              {result.screenshotPath && (
                <button
                  type="button"
                  onClick={() => setShowScreenshot(true)}
                  className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-yellow-300 bg-yellow-100 px-3 py-1.5 text-xs font-medium text-yellow-800 hover:bg-yellow-200"
                >
                  <Camera className="w-3 h-3" />
                  View Screenshot
                </button>
              )}
            </div>
          )}

          {result?.type === "manual" && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <ExternalLink className="w-5 h-5 text-amber-500 flex-shrink-0" />
                <div>
                  <p className="text-sm text-amber-800 font-medium">Manual application required</p>
                  <p className="text-xs text-amber-700 mt-1">
                    This job requires you to apply manually on the employer&apos;s site.
                  </p>
                </div>
              </div>
              <a
                href={result.manualUrl ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-700"
              >
                <ExternalLink className="w-3 h-3" />
                Apply Manually
              </a>
            </div>
          )}

          {result?.type === "failed" && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <div className="flex items-start gap-2">
                <XCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                <div>
                  <p className="text-sm text-red-800 font-medium">Application failed</p>
                  <p className="text-xs text-red-700 mt-1">{result.error}</p>
                </div>
              </div>
              <button
                type="button"
                onClick={handleRetry}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-red-700"
              >
                <RotateCcw className="w-3 h-3" />
                Retry
              </button>
            </div>
          )}
        </div>

        {showScreenshot && (
          <div className="fixed inset-0 z-[60] flex items-center justify-center">
            <div className="fixed inset-0 bg-black/60" onClick={() => setShowScreenshot(false)} />
            <div className="relative bg-white rounded-xl shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-auto">
              <div className="sticky top-0 bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-gray-900">Application Screenshot</h3>
                <button
                  type="button"
                  onClick={() => setShowScreenshot(false)}
                  className="rounded-lg p-1 hover:bg-gray-100"
                >
                  <X className="w-4 h-4 text-gray-500" />
                </button>
              </div>
              <div className="p-4">
                <p className="text-xs text-gray-500">
                  Screenshot captured during the auto-apply process.
                </p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
