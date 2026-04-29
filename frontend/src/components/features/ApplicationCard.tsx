import { MapPin, Banknote, ExternalLink } from "lucide-react";
import type { ApplicationListItem } from "@/types/application";

interface ApplicationCardProps {
  application: ApplicationListItem;
  onClick: () => void;
}

const STATUS_STYLES: Record<string, string> = {
  saved: "bg-gray-100 text-gray-700",
  generating: "bg-yellow-100 text-yellow-800",
  ready: "bg-blue-100 text-blue-800",
  applied: "bg-indigo-100 text-indigo-800",
  screening: "bg-purple-100 text-purple-800",
  interview: "bg-cyan-100 text-cyan-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  withdrawn: "bg-gray-100 text-gray-500",
};

function getSourceBadge(source: string) {
  const colors: Record<string, string> = {
    linkedin: "bg-blue-600 text-white",
    adzuna: "bg-orange-500 text-white",
    jsearch: "bg-indigo-600 text-white",
    remotive: "bg-emerald-600 text-white",
    reed: "bg-red-600 text-white",
  };
  return (
    <span
      className={`inline-flex items-center rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase ${colors[source] || "bg-gray-500 text-white"}`}
    >
      {source}
    </span>
  );
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-yellow-600";
  return "text-red-600";
}

export function ApplicationCard({ application, onClick }: ApplicationCardProps) {
  const { job, match_score } = application;

  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left rounded-lg border border-gray-200 bg-white p-4 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer"
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-1.5">
          {getSourceBadge(job.source)}
          <span
            className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium capitalize ${STATUS_STYLES[application.status] || "bg-gray-100 text-gray-700"}`}
          >
            {application.status}
          </span>
        </div>
        {match_score != null && (
          <span className={`text-xs font-bold ${getScoreColor(match_score)}`}>
            {Math.round(match_score)}%
          </span>
        )}
      </div>

      <h4 className="font-semibold text-gray-900 text-sm truncate">
        {job.title}
      </h4>
      <p className="text-xs text-gray-600">{job.company}</p>

      <div className="flex items-center gap-3 mt-2 text-xs text-gray-500">
        {job.location && (
          <span className="flex items-center gap-1">
            <MapPin className="w-3 h-3" />
            {job.location}
          </span>
        )}
        {job.salary_min != null && job.salary_max != null && (
          <span className="flex items-center gap-1">
            <Banknote className="w-3 h-3" />${job.salary_min.toLocaleString()} - $
            {job.salary_max.toLocaleString()}
          </span>
        )}
      </div>

      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-1">
          {application.resume_id && (
            <span className="inline-block w-2 h-2 rounded-full bg-blue-400" title="Resume linked" />
          )}
          {application.cover_letter_id && (
            <span className="inline-block w-2 h-2 rounded-full bg-green-400" title="Cover letter linked" />
          )}
          {application.interview_prep_id && (
            <span className="inline-block w-2 h-2 rounded-full bg-purple-400" title="Interview prep linked" />
          )}
        </div>
        <ExternalLink className="w-3.5 h-3.5 text-gray-400" />
      </div>
    </button>
  );
}
