import Link from "next/link";
import type { JobListItem } from "@/types/job";
import { formatSalary } from "@/lib/utils";

interface JobCardProps {
  job: JobListItem;
  isSaved?: boolean;
  selected?: boolean;
  onToggleSelect?: (jobId: string) => void;
  onSave?: (jobId: string) => void;
  onApply?: (jobId: string) => void;
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

function getScoreRingColor(score: number): string {
  if (score >= 80) return "stroke-green-500";
  if (score >= 60) return "stroke-yellow-500";
  return "stroke-red-500";
}

function getScoreBgColor(score: number): string {
  if (score >= 80) return "bg-green-50 border-green-200";
  if (score >= 60) return "bg-yellow-50 border-yellow-200";
  return "bg-red-50 border-red-200";
}

function getRemoteBadge(policy: string | null) {
  if (!policy) return null;
  const colors: Record<string, string> = {
    remote: "bg-blue-50 text-blue-700",
    hybrid: "bg-purple-50 text-purple-700",
    onsite: "bg-gray-50 text-gray-700",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colors[policy] || "bg-gray-50 text-gray-700"}`}>
      {policy.charAt(0).toUpperCase() + policy.slice(1)}
    </span>
  );
}

function getSourceBadge(source: string) {
  const colors: Record<string, string> = {
    linkedin: "bg-blue-600 text-white",
    adzuna: "bg-orange-500 text-white",
    jsearch: "bg-indigo-600 text-white",
    remotive: "bg-emerald-600 text-white",
    reed: "bg-red-600 text-white",
  };
  return (
    <span className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${colors[source] || "bg-gray-500 text-white"}`}>
      {source}
    </span>
  );
}

export function JobCard({ job, isSaved = false, selected = false, onToggleSelect, onSave, onApply }: JobCardProps) {
  const scoreRadius = 18;
  const circumference = 2 * Math.PI * scoreRadius;

  function handleCardClick(e: React.MouseEvent) {
    const target = e.target as HTMLElement;
    if (target.closest("button") || target.closest("a") || target.closest("input")) {
      return;
    }
  }

  return (
    <div
      className={`rounded-lg border bg-white p-5 hover:border-blue-300 hover:shadow-sm transition-all relative ${selected ? "border-blue-400 ring-1 ring-blue-400" : "border-gray-200"}`}
      onClick={handleCardClick}
    >
      <div className="absolute top-3 left-3 z-10">
        <input
          type="checkbox"
          checked={selected}
          onChange={(e) => {
            e.stopPropagation();
            onToggleSelect?.(job.id);
          }}
          className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500 cursor-pointer"
        />
      </div>

      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 ml-6">
          <div className="flex items-center gap-2 mb-1">
            <Link href={`/jobs/${job.id}`} className="inline-block">
              {getSourceBadge(job.source)}
            </Link>
            {job.remote_policy && getRemoteBadge(job.remote_policy)}
            {isSaved && (
              <svg className="w-3.5 h-3.5 text-blue-600 ml-auto" fill="currentColor" viewBox="0 0 24 24">
                <path d="M5 2h14a1 1 0 011 1v19.143a.5.5 0 01-.766.424L12 18.03l-7.234 4.536A.5.5 0 014 22.143V3a1 1 0 011-1z" />
              </svg>
            )}
          </div>
          <Link href={`/jobs/${job.id}`}>
            <h3 className="font-semibold text-gray-900 truncate hover:text-blue-600 transition-colors">{job.title}</h3>
          </Link>
          <p className="text-sm text-gray-600">{job.company}</p>
          {job.location && (
            <p className="text-sm text-gray-500 mt-0.5">{job.location}</p>
          )}
          {job.salary_min != null && job.salary_max != null && (
            <p className="text-sm font-medium text-gray-700 mt-1">
              {formatSalary(job.salary_min, job.salary_max, job.salary_currency || "USD")}
            </p>
          )}
        </div>

        <div className="flex-shrink-0">
          {job.match_score != null ? (
            <div className={`flex flex-col items-center rounded-lg border p-2 ${getScoreBgColor(job.match_score)}`}>
              <div className="relative w-12 h-12">
                <svg className="w-12 h-12 -rotate-90" viewBox="0 0 44 44">
                  <circle
                    cx="22" cy="22" r={scoreRadius}
                    fill="none" strokeWidth="3" className="stroke-gray-200"
                  />
                  <circle
                    cx="22" cy="22" r={scoreRadius}
                    fill="none" strokeWidth="3"
                    strokeDasharray={circumference}
                    strokeDashoffset={circumference - (job.match_score / 100) * circumference}
                    strokeLinecap="round"
                    className={getScoreRingColor(job.match_score)}
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className={`text-xs font-bold ${getScoreColor(job.match_score)}`}>
                    {Math.round(job.match_score)}
                  </span>
                </div>
              </div>
              <span className="text-[10px] text-gray-500 mt-0.5">Match</span>
            </div>
          ) : (
            <div className="flex flex-col items-center rounded-lg border border-gray-100 bg-gray-50 p-2">
              <span className="text-xs text-gray-400">Not scored</span>
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-100 flex items-center gap-1.5 flex-wrap">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSave?.(job.id);
          }}
          className={`inline-flex items-center gap-1 rounded-md px-2.5 py-1.5 text-xs font-medium transition-colors ${
            isSaved
              ? "bg-blue-50 text-blue-700 hover:bg-blue-100"
              : "bg-gray-50 text-gray-600 hover:bg-gray-100"
          }`}
          title={isSaved ? "Unsave job" : "Save job"}
        >
          <svg className="w-3.5 h-3.5" fill={isSaved ? "currentColor" : "none"} viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
          </svg>
          {isSaved ? "Saved" : "Save"}
        </button>

        <Link
          href={`/resumes/generate?job_id=${job.id}`}
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 rounded-md bg-gray-50 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          Resume
        </Link>

        <Link
          href={`/cover-letters/generate?job_id=${job.id}`}
          onClick={(e) => e.stopPropagation()}
          className="inline-flex items-center gap-1 rounded-md bg-gray-50 px-2.5 py-1.5 text-xs font-medium text-gray-600 hover:bg-gray-100 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" />
          </svg>
          Cover Letter
        </Link>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onApply?.(job.id);
          }}
          className="inline-flex items-center gap-1 rounded-md bg-orange-50 px-2.5 py-1.5 text-xs font-medium text-orange-700 hover:bg-orange-100 transition-colors"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 13.5l10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75z" />
          </svg>
          Apply
        </button>
      </div>
    </div>
  );
}
