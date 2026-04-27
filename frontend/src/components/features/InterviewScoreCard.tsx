"use client";

import type { SessionMessage } from "@/types/interview";

interface InterviewScoreCardProps {
  overallScore: number;
  messages: SessionMessage[];
  overallFeedback: string | null;
}

function getCategoryScores(messages: SessionMessage[]): Record<string, { total: number; count: number }> {
  const scores: Record<string, { total: number; count: number }> = {};
  for (const msg of messages) {
    if (msg.role === "coach" && msg.score !== null && msg.score !== undefined && msg.category) {
      if (!scores[msg.category]) {
        scores[msg.category] = { total: 0, count: 0 };
      }
      scores[msg.category].total += msg.score;
      scores[msg.category].count += 1;
    }
  }
  return scores;
}

const CATEGORY_LABELS: Record<string, string> = {
  company_research: "Company Research",
  technical: "Technical",
  behavioral: "Behavioral",
  culture_fit: "Culture Fit",
};

function getScoreColor(score: number): string {
  if (score >= 8) return "text-green-600";
  if (score >= 6) return "text-blue-600";
  if (score >= 4) return "text-yellow-600";
  return "text-red-600";
}

function getScoreRingColor(score: number): string {
  if (score >= 8) return "stroke-green-500";
  if (score >= 6) return "stroke-blue-500";
  if (score >= 4) return "stroke-yellow-500";
  return "stroke-red-500";
}

export function InterviewScoreCard({ overallScore, messages, overallFeedback }: InterviewScoreCardProps) {
  const categoryScores = getCategoryScores(messages);

  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (overallScore / 10) * circumference;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-6">Session Results</h3>

      <div className="flex flex-col items-center mb-8">
        <div className="relative w-32 h-32">
          <svg className="w-32 h-32 -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50" cy="50" r="45"
              fill="none" strokeWidth="8" className="stroke-gray-200"
            />
            <circle
              cx="50" cy="50" r="45"
              fill="none" strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              className={getScoreRingColor(overallScore)}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-3xl font-bold ${getScoreColor(overallScore)}`}>
              {overallScore.toFixed(1)}
            </span>
          </div>
        </div>
        <span className="mt-2 text-sm text-gray-500">Overall Score</span>
      </div>

      <div className="space-y-3 mb-6">
        {Object.entries(categoryScores).map(([category, data]) => {
          const avg = data.count > 0 ? data.total / data.count : 0;
          return (
            <div key={category} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                {CATEGORY_LABELS[category] || category}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      avg >= 7 ? "bg-green-500" : avg >= 5 ? "bg-blue-500" : avg >= 3 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${(avg / 10) * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900 w-8 text-right">
                  {avg.toFixed(1)}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {overallFeedback && (
        <div className="border-t border-gray-200 pt-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Coaching Summary</h4>
          <p className="text-sm text-gray-600 leading-relaxed">{overallFeedback}</p>
        </div>
      )}
    </div>
  );
}
