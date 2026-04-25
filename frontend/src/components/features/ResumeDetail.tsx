import type {
  ResumeResponse,
  ResumeContent,
  ATSResult,
  ATSKeywordCheck,
  ATSSectionCheck,
} from "@/types/resume";

function getAtsScoreBg(score: number | null): string {
  if (score === null) return "bg-gray-100 text-gray-600";
  if (score >= 80) return "bg-green-100 text-green-800";
  if (score >= 60) return "bg-yellow-100 text-yellow-800";
  return "bg-red-100 text-red-800";
}

function getAtsScoreRing(score: number | null): string {
  if (score === null) return "ring-gray-200";
  if (score >= 80) return "ring-green-200";
  if (score >= 60) return "ring-yellow-200";
  return "ring-red-200";
}

interface ATSBadgeProps {
  score: number | null;
}

function ATSBadge({ score }: ATSBadgeProps) {
  const label = score === null ? "Pending" : `${Math.round(score)}%`;
  return (
    <div
      className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 ring-1 ${getAtsScoreBg(score)} ${getAtsScoreRing(score)}`}
    >
      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75M21 12c0 1.268-.63 2.39-1.593 3.068a3.745 3.745 0 0 1-1.043 3.296 3.745 3.745 0 0 1-3.296 1.043A3.745 3.745 0 0 1 12 21c-1.268 0-2.39-.63-3.068-1.593a3.746 3.746 0 0 1-3.296-1.043 3.745 3.745 0 0 1-1.043-3.296A3.745 3.745 0 0 1 3 12c0-1.268.63-2.39 1.593-3.068a3.745 3.745 0 0 1 1.043-3.296 3.746 3.746 0 0 1 3.296-1.043A3.746 3.746 0 0 1 12 3c1.268 0 2.39.63 3.068 1.593a3.746 3.746 0 0 1 3.296 1.043 3.746 3.746 0 0 1 1.043 3.296A3.745 3.745 0 0 1 21 12Z" />
      </svg>
      <span className="text-sm font-semibold">ATS Score: {label}</span>
    </div>
  );
}

interface ATSBreakdownProps {
  breakdown: ATSResult;
}

function ATSBreakdown({ breakdown }: ATSBreakdownProps) {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{Math.round(breakdown.overall_score)}%</p>
          <p className="text-sm text-gray-500">Overall</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{Math.round(breakdown.keyword_score)}%</p>
          <p className="text-sm text-gray-500">Keywords</p>
        </div>
        <div className="rounded-lg border border-gray-200 p-4 text-center">
          <p className="text-2xl font-bold text-gray-900">{Math.round(breakdown.section_score)}%</p>
          <p className="text-sm text-gray-500">Sections</p>
        </div>
      </div>

      {breakdown.keyword_checks && breakdown.keyword_checks.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Keyword Checks</h4>
          <div className="flex flex-wrap gap-2">
            {breakdown.keyword_checks.map((check: ATSKeywordCheck) => (
              <span
                key={check.keyword}
                className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
                  check.found
                    ? "bg-green-50 text-green-700 ring-1 ring-green-200"
                    : "bg-red-50 text-red-700 ring-1 ring-red-200"
                }`}
              >
                {check.keyword} {check.found ? "✓" : "✗"}
              </span>
            ))}
          </div>
        </div>
      )}

      {breakdown.section_checks && breakdown.section_checks.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Section Checks</h4>
          <div className="space-y-1">
            {breakdown.section_checks.map((check: ATSSectionCheck) => (
              <div key={check.section} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{check.section}</span>
                <span className={check.present ? "text-green-600" : "text-red-600"}>
                  {check.present ? "Present" : "Missing"}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {breakdown.suggestions && breakdown.suggestions.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Suggestions</h4>
          <ul className="list-disc list-inside space-y-1 text-sm text-gray-600">
            {breakdown.suggestions.map((suggestion: string, i: number) => (
              <li key={i}>{suggestion}</li>
            ))}
          </ul>
        </div>
      )}

      {breakdown.missing_keywords && breakdown.missing_keywords.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Missing Keywords</h4>
          <div className="flex flex-wrap gap-2">
            {breakdown.missing_keywords.map((keyword: string) => (
              <span
                key={keyword}
                className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-700 ring-1 ring-red-200"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ResumeSectionsProps {
  contentJson: Record<string, unknown>;
}

function ResumeSections({ contentJson }: ResumeSectionsProps) {
  const content = contentJson as unknown as ResumeContent;

  if (!content.sections || content.sections.length === 0) {
    return <p className="text-gray-500 text-sm">No resume content available.</p>;
  }

  return (
    <div className="space-y-6">
      {content.sections
        .sort((a, b) => a.order - b.order)
        .map((section) => (
          <div key={section.title}>
            <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2 mb-3">
              {section.title}
            </h3>
            {section.content && (
              <p className="text-sm text-gray-700 whitespace-pre-wrap mb-3">
                {section.content}
              </p>
            )}
            {section.bullet_points && section.bullet_points.length > 0 && (
              <ul className="list-disc list-inside space-y-1.5">
                {section.bullet_points.map((bp, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    {bp.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}

      {content.target_keywords_covered && content.target_keywords_covered.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 border-b border-gray-200 pb-2 mb-3">
            Keywords Covered
          </h3>
          <div className="flex flex-wrap gap-2">
            {content.target_keywords_covered.map((keyword) => (
              <span
                key={keyword}
                className="inline-flex items-center rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-blue-200"
              >
                {keyword}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

interface ResumeDetailProps {
  resume: ResumeResponse;
}

export function ResumeDetail({ resume }: ResumeDetailProps) {
  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-gray-900">
            {resume.job_title || "Manual Resume"}
          </h2>
          {resume.company_name && (
            <p className="text-gray-500">{resume.company_name}</p>
          )}
        </div>
        <ATSBadge score={resume.ats_score} />
      </div>

      {resume.ats_breakdown && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">ATS Analysis</h3>
          <ATSBreakdown breakdown={resume.ats_breakdown as unknown as ATSResult} />
        </div>
      )}

      {resume.content_json && (
        <div className="rounded-lg border border-gray-200 bg-white p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Resume Content</h3>
          <ResumeSections contentJson={resume.content_json} />
        </div>
      )}
    </div>
  );
}
