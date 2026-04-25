import Link from "next/link";
import type { ResumeListItem } from "@/types/resume";

interface ResumeCardProps {
  resume: ResumeListItem;
}

function getAtsScoreColor(score: number | null): string {
  if (score === null) return "bg-gray-100 text-gray-600";
  if (score >= 80) return "bg-green-100 text-green-700";
  if (score >= 60) return "bg-yellow-100 text-yellow-700";
  return "bg-red-100 text-red-700";
}

function getAtsScoreLabel(score: number | null): string {
  if (score === null) return "Pending";
  return `${Math.round(score)}%`;
}

export function ResumeCard({ resume }: ResumeCardProps) {
  const title = resume.job_title || "Manual Resume";
  const company = resume.company_name || "";
  const dateStr = new Date(resume.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link href={`/resumes/${resume.id}`}>
      <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-gray-900 truncate">{title}</h3>
            {company && (
              <p className="mt-0.5 text-sm text-gray-500 truncate">
                {company}
              </p>
            )}
            <p className="mt-2 text-xs text-gray-400">{dateStr}</p>
          </div>
          <span
            className={`ml-3 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getAtsScoreColor(resume.ats_score)}`}
          >
            ATS: {getAtsScoreLabel(resume.ats_score)}
          </span>
        </div>
      </div>
    </Link>
  );
}
