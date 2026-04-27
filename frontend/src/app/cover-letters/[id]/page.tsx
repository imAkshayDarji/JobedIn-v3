"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { getCoverLetter, getCoverLetterStatus, deleteCoverLetter } from "@/lib/api/cover-letters";
import type { CoverLetterResponse } from "@/types/cover-letter";

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 80;

function getToneBadgeClasses(tone: string | null): string {
  switch (tone) {
    case "casual":
      return "bg-purple-100 text-purple-700";
    case "enthusiastic":
      return "bg-orange-100 text-orange-700";
    default:
      return "bg-blue-100 text-blue-700";
  }
}

export default function CoverLetterDetailPage() {
  const params = useParams();
  const router = useRouter();
  const coverLetterId = params.id as string;

  const [coverLetter, setCoverLetter] = useState<CoverLetterResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const loadCoverLetter = useCallback(async () => {
    try {
      const data = await getCoverLetter(coverLetterId);
      setCoverLetter(data);
      setIsGenerating(false);
    } catch (err: unknown) {
      if (err && typeof err === "object" && "status" in err) {
        const statusErr = err as { status: number; detail?: string };
        if (statusErr.status === 202) {
          setIsGenerating(true);
          return;
        }
      }
      const detail =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to load cover letter.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, [coverLetterId]);

  useEffect(() => {
    loadCoverLetter();
  }, [loadCoverLetter]);

  useEffect(() => {
    if (!isGenerating) return;

    let attempts = 0;
    let cancelled = false;

    const poll = async () => {
      if (cancelled) return;
      try {
        const status = await getCoverLetterStatus(coverLetterId);
        if (status.status === "completed") {
          await loadCoverLetter();
          return;
        }
        if (status.status === "failed") {
          setError("Cover letter generation failed. Please try again.");
          setIsGenerating(false);
          return;
        }
        attempts++;
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError("Generation is taking too long. Check back later.");
          setIsGenerating(false);
          return;
        }
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch {
        attempts++;
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError("Failed to check status.");
          setIsGenerating(false);
          return;
        }
        setTimeout(poll, POLL_INTERVAL_MS);
      }
    };

    setTimeout(poll, POLL_INTERVAL_MS);
    return () => { cancelled = true; };
  }, [isGenerating, coverLetterId, loadCoverLetter]);

  async function handleDelete() {
    try {
      await deleteCoverLetter(coverLetterId);
      router.push("/cover-letters");
    } catch {
      setError("Failed to delete cover letter.");
      setShowDeleteConfirm(false);
    }
  }

  async function handleRetry() {
    setLoading(true);
    setError(null);
    setIsGenerating(false);
    await loadCoverLetter();
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6">
          <Link
            href="/cover-letters"
            className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            Back to Cover Letters
          </Link>
        </div>

        {loading && (
          <div className="animate-pulse space-y-6">
            <div className="h-6 bg-gray-200 rounded w-1/3" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-32 bg-gray-200 rounded" />
            <div className="h-64 bg-gray-200 rounded" />
          </div>
        )}

        {isGenerating && !loading && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-4">
              <svg className="h-8 w-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Your cover letter is being generated...
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              This usually takes 15-60 seconds. We&apos;ll show it here when ready.
            </p>
          </div>
        )}

        {error && !loading && !isGenerating && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-50 mb-4">
              <svg className="h-8 w-8 text-red-500" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Something went wrong</h3>
            <p className="mt-2 text-sm text-red-600">{error}</p>
            <div className="mt-6 flex gap-3 justify-center">
              <button
                type="button"
                onClick={handleRetry}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Retry
              </button>
              <Link
                href="/cover-letters/generate"
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Generate New
              </Link>
            </div>
          </div>
        )}

        {coverLetter && !loading && !isGenerating && !error && (
          <>
            <div className="flex items-center gap-3 mb-8">
              <Link
                href="/cover-letters/generate"
                className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Regenerate
              </Link>
              {!showDeleteConfirm ? (
                <button
                  type="button"
                  onClick={() => setShowDeleteConfirm(true)}
                  className="rounded-md border border-red-300 bg-white px-3 py-1.5 text-sm font-medium text-red-600 hover:bg-red-50"
                >
                  Delete
                </button>
              ) : (
                <div className="flex items-center gap-2">
                  <span className="text-sm text-red-600">Are you sure?</span>
                  <button
                    type="button"
                    onClick={handleDelete}
                    className="rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
                  >
                    Yes, Delete
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowDeleteConfirm(false)}
                    className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>

            <div className="space-y-8">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">
                    {coverLetter.job_title || "Cover Letter"}
                  </h2>
                  {coverLetter.company_name && (
                    <p className="text-gray-500">{coverLetter.company_name}</p>
                  )}
                </div>
                {coverLetter.tone && (
                  <span
                    className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${getToneBadgeClasses(coverLetter.tone)}`}
                  >
                    {coverLetter.tone.charAt(0).toUpperCase() + coverLetter.tone.slice(1)}
                  </span>
                )}
              </div>

              {coverLetter.content && (
                <div className="rounded-lg border border-gray-200 bg-white p-6">
                  <div className="prose prose-sm max-w-none">
                    {coverLetter.content.split("\n\n").map((paragraph, i) => (
                      <p key={i} className="text-gray-700 whitespace-pre-wrap mb-4 last:mb-0">
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
