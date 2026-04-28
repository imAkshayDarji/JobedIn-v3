"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { JobMatchScore } from "@/components/features/JobMatchScore";
import { getJob, getJobScore } from "@/lib/api/jobs";
import type { JobDetail, MatchBreakdown } from "@/types/job";

export default function JobDetailPage() {
  const params = useParams();
  const router = useRouter();
  const jobId = params.id as string;

  const [job, setJob] = useState<JobDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [breakdown, setBreakdown] = useState<MatchBreakdown | null>(null);
  const [matchScore, setMatchScore] = useState<number | null>(null);
  const [matchedSkills, setMatchedSkills] = useState<string[]>([]);
  const [missingSkills, setMissingSkills] = useState<string[]>([]);

  useEffect(() => {
    loadJob();
  }, [jobId]);

  async function loadJob() {
    try {
      const data = await getJob(jobId);
      setJob(data);

      if (data.match_score != null && data.match_breakdown) {
        setMatchScore(data.match_score);
        setBreakdown(data.match_breakdown);
      } else {
        try {
          const scoreData = await getJobScore(jobId);
          setMatchScore(scoreData.match_score);
          setBreakdown(scoreData.breakdown);
          setMatchedSkills(scoreData.matched_skills);
          setMissingSkills(scoreData.missing_skills);
        } catch {
          // Score computation failed silently
        }
      }
    } catch {
      setJob(null);
    } finally {
      setLoading(false);
    }
  }

  if (loading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl px-6 py-8">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-2" />
            <div className="h-8 bg-gray-200 rounded w-1/2 mb-4" />
            <div className="h-64 bg-gray-200 rounded" />
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!job) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl px-6 py-8 text-center">
          <p className="text-gray-500">Job not found.</p>
          <Link href="/jobs" className="text-blue-600 hover:underline mt-2 inline-block">
            Back to Jobs
          </Link>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-8">
        <button
          onClick={() => router.back()}
          className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
          </svg>
          Back to Jobs
        </button>

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span className="inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase bg-indigo-600 text-white">
                  {job.source}
                </span>
                {job.remote_policy && (
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-blue-50 text-blue-700">
                    {job.remote_policy.charAt(0).toUpperCase() + job.remote_policy.slice(1)}
                  </span>
                )}
                {job.experience_level && (
                  <span className="inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium bg-gray-50 text-gray-700">
                    {job.experience_level.charAt(0).toUpperCase() + job.experience_level.slice(1)}
                  </span>
                )}
              </div>
              <h1 className="text-2xl font-bold text-gray-900">{job.title}</h1>
              <p className="text-lg text-gray-600">{job.company}</p>
            </div>

            <div className="grid grid-cols-2 gap-4 text-sm">
              {job.location && (
                <div>
                  <span className="text-gray-500">Location</span>
                  <p className="font-medium text-gray-900">{job.location}</p>
                </div>
              )}
              {job.salary_min != null && job.salary_max != null && (
                <div>
                  <span className="text-gray-500">Salary</span>
                  <p className="font-medium text-gray-900">
                    ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()} {job.salary_currency}
                  </p>
                </div>
              )}
              {job.job_type && (
                <div>
                  <span className="text-gray-500">Job Type</span>
                  <p className="font-medium text-gray-900">{job.job_type}</p>
                </div>
              )}
              {job.ats_platform && (
                <div>
                  <span className="text-gray-500">ATS Platform</span>
                  <p className="font-medium text-gray-900">{job.ats_platform}</p>
                </div>
              )}
            </div>

            {job.description && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-2">Description</h2>
                <div className="prose prose-sm max-w-none text-gray-700 whitespace-pre-wrap">
                  {job.description}
                </div>
              </div>
            )}

            <div className="flex items-center gap-3 pt-4 border-t border-gray-200">
              {job.apply_url && (
                <a
                  href={job.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
                >
                  Apply Now
                </a>
              )}
              <button className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Generate Resume
              </button>
              <button className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50">
                Generate Cover Letter
              </button>
            </div>
          </div>

          <div className="space-y-4">
            {matchScore != null && breakdown && (
              <JobMatchScore
                matchScore={matchScore}
                breakdown={breakdown}
                matchedSkills={matchedSkills}
                missingSkills={missingSkills}
              />
            )}

            {job.source_url && (
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Source</h3>
                <a
                  href={job.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 hover:underline"
                >
                  View on {job.source.charAt(0).toUpperCase() + job.source.slice(1)}
                </a>
              </div>
            )}

            {job.alternate_sources && job.alternate_sources.length > 0 && (
              <div className="rounded-lg border border-gray-200 bg-white p-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Also Found On</h3>
                <div className="space-y-1">
                  {job.alternate_sources.map((alt, i) => (
                    <span key={i} className="inline-flex items-center rounded px-1.5 py-0.5 text-xs font-medium bg-gray-50 text-gray-600 mr-1">
                      {(alt as Record<string, unknown>).source as string}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
