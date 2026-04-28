"use client";

import type { MatchBreakdown } from "@/types/job";

interface JobMatchScoreProps {
  matchScore: number;
  breakdown: MatchBreakdown;
  matchedSkills: string[];
  missingSkills: string[];
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

function getBarColor(score: number): string {
  if (score >= 0.8) return "bg-green-500";
  if (score >= 0.6) return "bg-yellow-500";
  return "bg-red-500";
}

const DIMENSIONS: { key: keyof MatchBreakdown; label: string; weight: string }[] = [
  { key: "skills_score", label: "Skills", weight: "40%" },
  { key: "experience_score", label: "Experience", weight: "25%" },
  { key: "role_relevance_score", label: "Role Relevance", weight: "25%" },
  { key: "location_score", label: "Location", weight: "10%" },
];

export function JobMatchScore({
  matchScore,
  breakdown,
  matchedSkills,
  missingSkills,
}: JobMatchScoreProps) {
  const circumference = 2 * Math.PI * 45;
  const offset = circumference - (matchScore / 100) * circumference;

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6">
      <h3 className="text-lg font-bold text-gray-900 mb-6">Match Score</h3>

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
              className={getScoreRingColor(matchScore)}
            />
          </svg>
          <div className="absolute inset-0 flex items-center justify-center">
            <span className={`text-3xl font-bold ${getScoreColor(matchScore)}`}>
              {Math.round(matchScore)}
            </span>
          </div>
        </div>
        <span className="mt-2 text-sm text-gray-500">Overall Match</span>
      </div>

      <div className="space-y-3 mb-6">
        {DIMENSIONS.map(({ key, label, weight }) => {
          const value = breakdown[key];
          return (
            <div key={key} className="flex items-center justify-between">
              <span className="text-sm text-gray-600">
                {label} <span className="text-gray-400">({weight})</span>
              </span>
              <div className="flex items-center gap-2">
                <div className="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${getBarColor(value)}`}
                    style={{ width: `${value * 100}%` }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-900 w-10 text-right">
                  {Math.round(value * 100)}%
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {matchedSkills.length > 0 && (
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Matched Skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {matchedSkills.map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center rounded-full bg-green-50 px-2.5 py-0.5 text-xs font-medium text-green-700"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}

      {missingSkills.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-gray-700 mb-2">Missing Skills</h4>
          <div className="flex flex-wrap gap-1.5">
            {missingSkills.map((skill) => (
              <span
                key={skill}
                className="inline-flex items-center rounded-full bg-red-50 px-2.5 py-0.5 text-xs font-medium text-red-600"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
