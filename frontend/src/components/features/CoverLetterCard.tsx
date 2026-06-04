import Link from "next/link";
import { CoverLetterDownloadButton } from "@/components/features/CoverLetterDownloadButton";
import type { CoverLetterListItem } from "@/types/cover-letter";

interface CoverLetterCardProps {
  coverLetter: CoverLetterListItem;
}

function getToneBadgeClasses(tone: string | null): string {
  switch (tone) {
    case "casual":
      return "bg-purple-100 text-purple-700";
    case "enthusiastic":
      return "bg-orange-100 text-orange-700";
    default:
      return "bg-blue-100 text-blue-700";
  }
}

export function CoverLetterCard({ coverLetter }: CoverLetterCardProps) {
  const title = coverLetter.job_title || "Manual Cover Letter";
  const company = coverLetter.company_name || "";
  const dateStr = new Date(coverLetter.created_at).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between">
        <Link href={`/cover-letters/${coverLetter.id}`} className="min-w-0 flex-1">
          <h3 className="font-semibold text-gray-900 truncate">{title}</h3>
          {company && (
            <p className="mt-0.5 text-sm text-gray-500 truncate">{company}</p>
          )}
          <p className="mt-2 text-xs text-gray-400">{dateStr}</p>
        </Link>
        <span
          className={`ml-3 inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${getToneBadgeClasses(coverLetter.tone)}`}
        >
          {coverLetter.tone || "Professional"}
        </span>
      </div>
      <div className="mt-3 flex items-center gap-3">
        <Link
          href={`/cover-letters/${coverLetter.id}`}
          className="text-sm text-blue-600 hover:underline"
        >
          View
        </Link>
        <CoverLetterDownloadButton coverLetterId={coverLetter.id} />
      </div>
    </div>
  );
}
