import Link from "next/link";
import type { InterviewPrepListItem } from "@/types/interview";

interface InterviewCardProps {
  prep: InterviewPrepListItem;
}

const CATEGORY_LABELS: Record<string, string> = {
  company_research: "Research",
  technical: "Technical",
  behavioral: "Behavioral",
  culture_fit: "Culture",
};

function getStatusClasses(status: string): string {
  switch (status) {
    case "completed":
      return "bg-green-100 text-green-700";
    case "generating":
      return "bg-yellow-100 text-yellow-700";
    case "failed":
      return "bg-red-100 text-red-700";
    default:
      return "bg-gray-100 text-gray-700";
  }
}

export function InterviewCard({ prep }: InterviewCardProps) {
  const title = prep.job_title || "Interview Prep";
  const company = prep.company_name || "";
  const dateStr = new Date(prep.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <Link href={`/interview/coach?prepId=${prep.id}`}>
      <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-sm transition-all cursor-pointer">
        <div className="flex items-start justify-between">
          <div className="min-w-0 flex-1">
            <h3 className="font-semibold text-gray-900 truncate">{title}</h3>
            {company && (
              <p className="mt-0.5 text-sm text-gray-500 truncate">{company}</p>
            )}
            <div className="mt-2 flex items-center gap-2">
              <span className="text-xs text-gray-400">{dateStr}</span>
              {prep.question_count > 0 && (
                <span className="text-xs text-gray-400">
                  &middot; {prep.question_count} questions
                </span>
              )}
            </div>
          </div>
          <span
            className={`ml-3 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getStatusClasses(prep.status)}`}
          >
            {prep.status.charAt(0).toUpperCase() + prep.status.slice(1)}
          </span>
        </div>
      </div>
    </Link>
  );
}
