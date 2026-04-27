"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { InterviewScoreCard } from "@/components/features/InterviewScoreCard";
import { getInterviewSession } from "@/lib/api/interview";
import type { InterviewSessionDetail } from "@/types/interview";

function getRoleStyles(role: string): string {
  switch (role) {
    case "question":
      return "bg-blue-50 border-blue-200";
    case "user":
      return "bg-white border-gray-200";
    case "coach":
      return "bg-amber-50 border-amber-200";
    case "summary":
      return "bg-green-50 border-green-200";
    default:
      return "bg-gray-50 border-gray-200";
  }
}

function getRoleLabel(role: string): string {
  switch (role) {
    case "question":
      return "Interviewer";
    case "user":
      return "You";
    case "coach":
      return "Coach";
    case "summary":
      return "Session Summary";
    default:
      return role;
  }
}

export default function InterviewSessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.id as string;

  const [session, setSession] = useState<InterviewSessionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSession = useCallback(async () => {
    try {
      const data = await getInterviewSession(sessionId);
      setSession(data);
    } catch (err) {
      const detail = err && typeof err === "object" && "detail" in err
        ? (err as { detail: string }).detail
        : "Failed to load session.";
      setError(detail);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  return (
    <AppLayout>
      <div className="mx-auto max-w-4xl px-6 py-8">
        <div className="mb-6">
          <Link
            href="/interview"
            className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            Back to Interview Coach
          </Link>
        </div>

        {loading && (
          <div className="animate-pulse space-y-6">
            <div className="h-6 bg-gray-200 rounded w-1/3" />
            <div className="h-4 bg-gray-200 rounded w-1/4" />
            <div className="h-32 bg-gray-200 rounded" />
          </div>
        )}

        {error && !loading && (
          <div className="text-center py-16">
            <p className="text-red-600 mb-4">{error}</p>
            <button
              type="button"
              onClick={() => { setLoading(true); setError(null); loadSession(); }}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        )}

        {session && !loading && !error && (
          <>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Session Review</h2>
                <p className="text-sm text-gray-500 mt-1">
                  {session.questions_answered} question{session.questions_answered !== 1 ? "s" : ""} answered
                  {session.status === "active" && " (In Progress)"}
                </p>
              </div>
              {session.status === "completed" && session.overall_score !== null && (
                <span className="text-2xl font-bold text-blue-600">
                  {session.overall_score.toFixed(1)}/10
                </span>
              )}
            </div>

            {session.status === "completed" && (
              <div className="mb-8">
                <InterviewScoreCard
                  overallScore={session.overall_score || 0}
                  messages={session.messages}
                  overallFeedback={session.overall_feedback}
                />
              </div>
            )}

            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Conversation</h3>
              {session.messages.map((msg, i) => (
                <div
                  key={i}
                  className={`rounded-lg border p-4 ${getRoleStyles(msg.role)}`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-gray-600 uppercase">
                      {getRoleLabel(msg.role)}
                    </span>
                    <div className="flex items-center gap-2">
                      {msg.score !== null && msg.score !== undefined && (
                        <span className="text-xs font-medium text-gray-500">
                          Score: {msg.score}/10
                        </span>
                      )}
                      {msg.difficulty !== null && msg.difficulty !== undefined && (
                        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600">
                          Level {msg.difficulty}
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-sm text-gray-800 whitespace-pre-wrap">
                    {msg.content}
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-8 flex gap-3">
              <Link
                href={`/interview/coach?prepId=${session.prep_id}`}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Practice Again
              </Link>
              <Link
                href="/interview"
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Back to List
              </Link>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
