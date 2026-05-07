"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { generateResume, generateResumeManual, getResumeStatus } from "@/lib/api/resumes";
import { getJob } from "@/lib/api/jobs";
import type { JobDetail } from "@/types/job";

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 80;

export default function GenerateResumePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const jobId = searchParams.get("job_id");

  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resumeId, setResumeId] = useState<string | null>(null);

  const [jobContext, setJobContext] = useState<JobDetail | null>(null);
  const [jobContextLoading, setJobContextLoading] = useState(false);

  useEffect(() => {
    if (jobId) {
      loadJobContext(jobId);
    }
  }, [jobId]);

  async function loadJobContext(id: string) {
    setJobContextLoading(true);
    try {
      const job = await getJob(id);
      setJobContext(job);
      setJobDescription(job.description || "");
      setCompanyName(job.company);
      setJobTitle(job.title);

      // Auto-trigger generation if we have a job
      await handleGenerateFromJob(id);
    } catch {
      setError("Failed to load job details. You can still use the manual form below.");
    } finally {
      setJobContextLoading(false);
    }
  }

  async function handleGenerateFromJob(id: string) {
    setLoading(true);
    setError(null);

    try {
      const result = await generateResume({ job_id: id });
      setResumeId(result.resume_id);

      if (result.status === "completed") {
        router.push(`/resumes/${result.resume_id}`);
        return;
      }

      startPolling(result.resume_id);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to start resume generation. Please try again.";
      setError(message);
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const result = await generateResumeManual({
        job_description: jobDescription,
        company_name: companyName || undefined,
        job_title: jobTitle || undefined,
      });

      setResumeId(result.resume_id);

      if (result.status === "completed") {
        router.push(`/resumes/${result.resume_id}`);
        return;
      }

      startPolling(result.resume_id);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to start resume generation. Please try again.";
      setError(message);
      setLoading(false);
    }
  }

  function startPolling(id: string) {
    let attempts = 0;
    const poll = async () => {
      try {
        const status = await getResumeStatus(id);
        if (status.status === "completed") {
          router.push(`/resumes/${id}`);
          return;
        }
        if (status.status === "failed") {
          setError("Resume generation failed. Please try again.");
          setLoading(false);
          return;
        }
        attempts++;
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError("Resume generation is taking too long. Check your resumes list.");
          setLoading(false);
          return;
        }
        setTimeout(poll, POLL_INTERVAL_MS);
      } catch {
        attempts++;
        if (attempts >= MAX_POLL_ATTEMPTS) {
          setError("Failed to check generation status. Please check your resumes list.");
          setLoading(false);
          return;
        }
        setTimeout(poll, POLL_INTERVAL_MS);
      }
    };
    setTimeout(poll, POLL_INTERVAL_MS);
  }

  const descriptionLength = jobDescription.length;
  const isDescriptionValid = descriptionLength >= 50 && descriptionLength <= 10000;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-8">
          <Link
            href="/resumes"
            className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            Back to Resumes
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            Generate Resume
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {jobContext
              ? `Creating a tailored resume for ${jobContext.title} at ${jobContext.company}`
              : "Paste a job description and we'll create a tailored resume optimized for ATS."}
          </p>
        </div>

        {loading || jobContextLoading ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-4">
              <svg className="h-8 w-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Generating your tailored resume...
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              This usually takes 30-120 seconds. We'll redirect you when it's ready.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="job_description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Job Description <span className="text-red-500">*</span>
              </label>
              <textarea
                id="job_description"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                rows={10}
                placeholder="Paste the full job description here..."
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
                required
                minLength={50}
                maxLength={10000}
              />
              <div className="mt-1 flex justify-between text-xs text-gray-400">
                <span>Minimum 50 characters</span>
                <span className={descriptionLength > 9500 ? "text-red-500" : ""}>
                  {descriptionLength.toLocaleString()} / 10,000
                </span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="company_name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Company Name <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  id="company_name"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g., Google"
                  maxLength={200}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="job_title"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Job Title <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  id="job_title"
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g., Senior Backend Engineer"
                  maxLength={200}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={!isDescriptionValid || loading}
                className="rounded-md bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Generate Resume
              </button>
              <Link
                href="/resumes"
                className="rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </Link>
            </div>
          </form>
        )}
      </div>
    </AppLayout>
  );
}
