"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { CoverLetterCard } from "@/components/features/CoverLetterCard";
import { listCoverLetters } from "@/lib/api/cover-letters";
import type { CoverLetterListItem } from "@/types/cover-letter";

export default function CoverLettersPage() {
  const [coverLetters, setCoverLetters] = useState<CoverLetterListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadCoverLetters() {
      try {
        const data = await listCoverLetters();
        setCoverLetters(data.cover_letters);
        setTotal(data.total);
      } catch (err) {
        setError("Failed to load cover letters. Please try again.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadCoverLetters();
  }, []);

  async function handleRetry() {
    setLoading(true);
    setError(null);
    try {
      const data = await listCoverLetters();
      setCoverLetters(data.cover_letters);
      setTotal(data.total);
    } catch (err) {
      setError("Failed to load cover letters. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Cover Letters</h1>
            <p className="mt-1 text-sm text-gray-500">
              {total} cover letter{total !== 1 ? "s" : ""} generated
            </p>
          </div>
          <Link
            href="/cover-letters/generate"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Generate Cover Letter
          </Link>
        </div>

        {loading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-200 bg-white p-5 animate-pulse"
              >
                <div className="h-4 bg-gray-200 rounded w-3/4 mb-2" />
                <div className="h-3 bg-gray-200 rounded w-1/2 mb-4" />
                <div className="h-3 bg-gray-200 rounded w-1/4" />
              </div>
            ))}
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-12">
            <p className="text-red-600 mb-4">{error}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && coverLetters.length === 0 && (
          <div className="text-center py-16">
            <svg
              className="mx-auto h-12 w-12 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
              />
            </svg>
            <h3 className="mt-2 text-sm font-semibold text-gray-900">
              No cover letters yet
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              You haven&apos;t generated any cover letters yet.
            </p>
            <div className="mt-6">
              <Link
                href="/cover-letters/generate"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Generate Your First Cover Letter
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && coverLetters.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {coverLetters.map((cl) => (
              <CoverLetterCard key={cl.id} coverLetter={cl} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
