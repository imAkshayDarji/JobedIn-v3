"use client";

import { useState } from "react";
import Link from "next/link";
import { saveJob, unsaveJob } from "@/lib/api/jobs";
import { applyBulk } from "@/lib/api/apply";

interface BulkActionToolbarProps {
  selectedJobIds: string[];
  onClearSelection: () => void;
  onActionComplete: () => void;
}

export function BulkActionToolbar({
  selectedJobIds,
  onClearSelection,
  onActionComplete,
}: BulkActionToolbarProps) {
  const [saving, setSaving] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleBulkSave() {
    setSaving(true);
    setError(null);
    let savedCount = 0;
    let failedCount = 0;

    await Promise.allSettled(
      selectedJobIds.map(async (jobId) => {
        try {
          await saveJob(jobId);
          savedCount++;
        } catch {
          failedCount++;
        }
      }),
    );

    setSaving(false);
    onActionComplete();

    if (failedCount > 0 && savedCount === 0) {
      setError("Failed to save selected jobs. They may already be saved.");
    }
  }

  async function handleBulkApply() {
    if (selectedJobIds.length > 10) {
      setError("You can apply to a maximum of 10 jobs at once.");
      return;
    }

    setApplying(true);
    setError(null);

    try {
      // Save all first, then apply
      const saveResults = await Promise.allSettled(
        selectedJobIds.map((jobId) => saveJob(jobId)),
      );

      const savedIds: string[] = [];
      for (let i = 0; i < saveResults.length; i++) {
        const result = saveResults[i];
        if (result.status === "fulfilled") {
          savedIds.push(selectedJobIds[i]);
        }
      }

      if (savedIds.length === 0) {
        setError("No jobs could be saved for bulk apply.");
        setApplying(false);
        return;
      }

      await applyBulk(savedIds);
      onActionComplete();
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "message" in err
          ? (err as { message: string }).message
          : "Bulk apply failed. Please try again.";
      setError(message);
    } finally {
      setApplying(false);
    }
  }

  function getBulkResumeLink() {
    return `/resumes/generate?job_ids=${selectedJobIds.join(",")}`;
  }

  function getBulkCoverLetterLink() {
    return `/cover-letters/generate?job_ids=${selectedJobIds.join(",")}`;
  }

  return (
    <div className="fixed bottom-0 left-0 right-0 z-40 bg-white border-t border-gray-200 shadow-lg">
      <div className="mx-auto max-w-7xl px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-900">
            {selectedJobIds.length} selected
          </span>
          <button
            type="button"
            onClick={onClearSelection}
            className="text-sm text-gray-500 hover:text-gray-700 underline"
          >
            Clear
          </button>
          {error && (
            <span className="text-sm text-red-600">{error}</span>
          )}
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleBulkSave}
            disabled={saving}
            className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {saving ? "Saving..." : "Save All"}
          </button>

          <Link
            href={getBulkResumeLink()}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Generate Resumes
          </Link>

          <Link
            href={getBulkCoverLetterLink()}
            className="inline-flex items-center gap-1.5 rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Generate CLs
          </Link>

          <button
            type="button"
            onClick={handleBulkApply}
            disabled={applying || selectedJobIds.length > 10}
            className="inline-flex items-center gap-1.5 rounded-md bg-orange-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-orange-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {applying ? "Applying..." : `Bulk Apply (${selectedJobIds.length})`}
          </button>
        </div>
      </div>
    </div>
  );
}
