"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { ResumeCard } from "@/components/features/ResumeCard";
import { listResumes } from "@/lib/api/resumes";
import type { ResumeListItem } from "@/types/resume";

export default function ResumesPage() {
  const [resumes, setResumes] = useState<ResumeListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadResumes() {
      try {
        const data = await listResumes();
        setResumes(data.resumes);
        setTotal(data.total);
      } catch (err) {
        setError("Failed to load resumes. Please try again.");
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    loadResumes();
  }, []);

  async function handleRetry() {
    setLoading(true);
    setError(null);
    try {
      const data = await listResumes();
      setResumes(data.resumes);
      setTotal(data.total);
    } catch (err) {
      setError("Failed to load resumes. Please try again.");
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
            <h1 className="text-2xl font-bold text-gray-900">Resumes</h1>
            <p className="mt-1 text-sm text-gray-500">
              {total} resume{total !== 1 ? "s" : ""} generated
            </p>
          </div>
          <Link
            href="/resumes/generate"
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Generate Resume
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

        {!loading && !error && resumes.length === 0 && (
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
              No resumes yet
            </h3>
            <p className="mt-1 text-sm text-gray-500">
              You haven&apos;t generated any resumes yet.
            </p>
            <div className="mt-6">
              <Link
                href="/resumes/generate"
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Generate Your First Resume
              </Link>
            </div>
          </div>
        )}

        {!loading && !error && resumes.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {resumes.map((resume) => (
              <ResumeCard key={resume.id} resume={resume} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
