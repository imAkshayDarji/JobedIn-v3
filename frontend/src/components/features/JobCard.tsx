import Link from "next/link";
import type { JobListItem } from "@/types/job";

interface JobCardProps {
  job: JobListItem;
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

export function JobCard({ job }: JobCardProps) {
  const scoreRadius = 18;
  const circumference = 2 * Math.PI * scoreRadius;

  return (
    <Link href={`/jobs/${job.id}`} className="block">
      <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2 mb-1">
              {getSourceBadge(job.source)}
              {job.remote_policy && getRemoteBadge(job.remote_policy)}
            </div>
            <h3 className="font-semibold text-gray-900 truncate">{job.title}</h3>
            <p className="text-sm text-gray-600">{job.company}</p>
            {job.location && (
              <p className="text-sm text-gray-500 mt-0.5">{job.location}</p>
            )}
            {job.salary_min != null && job.salary_max != null && (
              <p className="text-sm font-medium text-gray-700 mt-1">
                ${job.salary_min.toLocaleString()} - ${job.salary_max.toLocaleString()}
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
      </div>
    </Link>
  );
}
