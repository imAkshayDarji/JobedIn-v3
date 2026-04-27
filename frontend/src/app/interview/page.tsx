"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { InterviewCard } from "@/components/features/InterviewCard";
import { listInterviewPreps } from "@/lib/api/interview";
import type { InterviewPrepListItem } from "@/types/interview";

export default function InterviewListPage() {
  const [preps, setPreps] = useState<InterviewPrepListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showSetup, setShowSetup] = useState(false);
  const [setupMode, setSetupMode] = useState<"job" | "manual">("manual");
  const [jobDescription, setJobDescription] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    loadPreps();
  }, []);

  async function loadPreps() {
    try {
      const data = await listInterviewPreps();
      setPreps(data.preps);
      setTotal(data.total);
    } catch (err) {
      setError("Failed to load interview preps. Please try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  async function handleSetup() {
    if (!jobDescription.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      const { setupInterviewPrep } = await import("@/lib/api/interview");
      await setupInterviewPrep({
        job_description: jobDescription,
        job_title: jobTitle || undefined,
        company_name: companyName || undefined,
      });
      setShowSetup(false);
      setJobDescription("");
      setJobTitle("");
      setCompanyName("");
      setLoading(true);
      await loadPreps();
    } catch (err) {
      setError("Failed to start interview prep. Please try again.");
      console.error(err);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Interview Coach</h1>
            <p className="mt-1 text-sm text-gray-500">
              {total} prep session{total !== 1 ? "s" : ""} created
            </p>
          </div>
          <button
            type="button"
            onClick={() => setShowSetup(true)}
            className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
          >
            Start New Prep
          </button>
        </div>

        {showSetup && (
          <div className="mb-8 rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Create Interview Prep</h2>
            <p className="text-sm text-gray-500 mb-4">
              Paste a job description and we&apos;ll generate a tailored question bank across 4 categories at 3 difficulty levels.
            </p>

            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label htmlFor="job-title" className="block text-sm font-medium text-gray-700 mb-1">
                    Job Title (optional)
                  </label>
                  <input
                    id="job-title"
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    placeholder="e.g. Senior Software Engineer"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
                <div>
                  <label htmlFor="company-name" className="block text-sm font-medium text-gray-700 mb-1">
                    Company Name (optional)
                  </label>
                  <input
                    id="company-name"
                    type="text"
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="e.g. Acme Corp"
                    className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="job-description" className="block text-sm font-medium text-gray-700 mb-1">
                  Job Description
                </label>
                <textarea
                  id="job-description"
                  value={jobDescription}
                  onChange={(e) => setJobDescription(e.target.value)}
                  placeholder="Paste the job description here..."
                  rows={6}
                  className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleSetup}
                  disabled={!jobDescription.trim() || submitting}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {submitting ? "Generating..." : "Generate Question Bank"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowSetup(false)}
                  className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {loading && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="rounded-lg border border-gray-200 bg-white p-5 animate-pulse">
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
              onClick={() => { setLoading(true); setError(null); loadPreps(); }}
              className="rounded-md bg-white px-4 py-2 text-sm font-medium text-gray-700 border border-gray-300 hover:bg-gray-50"
            >
              Retry
            </button>
          </div>
        )}

        {!loading && !error && preps.length === 0 && (
          <div className="text-center py-16">
            <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 0 1-.825-.242m9.345-8.334a2.126 2.126 0 0 0-.476-.095 48.64 48.64 0 0 0-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0 0 11.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" />
            </svg>
            <h3 className="mt-2 text-sm font-semibold text-gray-900">No interview preps yet</h3>
            <p className="mt-1 text-sm text-gray-500">
              Create your first interview prep to start practicing.
            </p>
            <div className="mt-6">
              <button
                type="button"
                onClick={() => setShowSetup(true)}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Create Your First Prep
              </button>
            </div>
          </div>
        )}

        {!loading && !error && preps.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {preps.map((p) => (
              <InterviewCard key={p.id} prep={p} />
            ))}
          </div>
        )}
      </div>
    </AppLayout>
  );
}
