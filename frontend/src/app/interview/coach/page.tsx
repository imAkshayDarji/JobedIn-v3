"use client";

import { Suspense, useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { InterviewChat } from "@/components/features/InterviewChat";
import { InterviewScoreCard } from "@/components/features/InterviewScoreCard";
import { getInterviewPrepStatus, sendChatMessage } from "@/lib/api/interview";
import type { SessionMessage, InterviewChatResponse, ChatQuestion } from "@/types/interview";

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 80;

export default function InterviewCoachPage() {
  return (
    <Suspense
      fallback={
        <AppLayout>
          <div className="mx-auto max-w-4xl px-6 py-16 text-center">
            <div className="animate-spin inline-block h-8 w-8 rounded-full border-4 border-blue-600 border-t-transparent" />
            <p className="mt-4 text-sm text-gray-500">Loading interview coach...</p>
          </div>
        </AppLayout>
      }
    >
      <InterviewCoachContent />
    </Suspense>
  );
}

function InterviewCoachContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const prepId = searchParams.get("prepId");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [questionCount, setQuestionCount] = useState(0);

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SessionMessage[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState<ChatQuestion | null>(null);
  const [difficulty, setDifficulty] = useState(1);
  const [questionsAnswered, setQuestionsAnswered] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [overallScore, setOverallScore] = useState(0);
  const [overallFeedback, setOverallFeedback] = useState<string | null>(null);

  const [answer, setAnswer] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const pollStatus = useCallback(async () => {
    if (!prepId) return;
    try {
      const status = await getInterviewPrepStatus(prepId);
      if (status.status === "completed") {
        setIsGenerating(false);
        setQuestionCount(status.question_count);
        setLoading(false);
        return;
      }
      if (status.status === "failed") {
        setError("Question generation failed. Please try again.");
        setIsGenerating(false);
        setLoading(false);
        return;
      }
    } catch {
      // continue polling
    }
  }, [prepId]);

  useEffect(() => {
    if (!prepId) {
      setError("No prep ID provided.");
      setLoading(false);
      return;
    }

    let attempts = 0;
    let cancelled = false;

    async function checkAndPoll() {
      if (cancelled) return;
      const status = await getInterviewPrepStatus(prepId!);
      if (status.status === "completed") {
        setIsGenerating(false);
        setQuestionCount(status.question_count);
        setLoading(false);
        return;
      }
      if (status.status === "failed") {
        setError("Question generation failed.");
        setLoading(false);
        return;
      }

      setIsGenerating(true);
      setLoading(false);

      const poll = async () => {
        if (cancelled) return;
        try {
          const s = await getInterviewPrepStatus(prepId!);
          if (s.status === "completed") {
            setIsGenerating(false);
            setQuestionCount(s.question_count);
            return;
          }
          if (s.status === "failed") {
            setError("Question generation failed.");
            setIsGenerating(false);
            return;
          }
          attempts++;
          if (attempts >= MAX_POLL_ATTEMPTS) {
            setError("Generation is taking too long. Check back later.");
            setIsGenerating(false);
            return;
          }
          setTimeout(poll, POLL_INTERVAL_MS);
        } catch {
          attempts++;
          if (attempts >= MAX_POLL_ATTEMPTS) {
            setError("Failed to check status.");
            setIsGenerating(false);
            return;
          }
          setTimeout(poll, POLL_INTERVAL_MS);
        }
      };
      setTimeout(poll, POLL_INTERVAL_MS);
    }

    checkAndPoll();
    return () => { cancelled = true; };
  }, [prepId]);

  async function startSession() {
    if (!prepId) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const data = await sendChatMessage({ prep_id: prepId });
      setSessionId(data.session_id);
      if (data.next_question) {
        setCurrentQuestion(data.next_question);
        setMessages((prev) => [
          ...prev,
          {
            role: "question",
            content: data.next_question!.question,
            score: null,
            category: data.next_question!.category,
            difficulty: data.next_question!.difficulty,
          },
        ]);
      }
      setDifficulty(data.difficulty);
    } catch (err) {
      const detail = err && typeof err === "object" && "detail" in err
        ? (err as { detail: string }).detail
        : "Failed to start session.";
      setError(detail);
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSubmitAnswer() {
    if (!prepId || !sessionId || !answer.trim()) return;
    setIsSubmitting(true);
    setError(null);

    const currentQ = currentQuestion;
    const userAnswer = answer.trim();
    setAnswer("");

    setMessages((prev) => [
      ...prev,
      {
        role: "user",
        content: userAnswer,
        score: null,
        category: currentQ?.category || null,
        difficulty: currentQ?.difficulty || null,
      },
    ]);

    try {
      const data = await sendChatMessage({
        prep_id: prepId,
        session_id: sessionId,
        answer: userAnswer,
      });

      if (data.evaluation) {
        const evalContent = [
          `Score: ${data.evaluation.score}/10`,
          "",
          "**Strengths:**",
          ...data.evaluation.strengths.map((s) => `- ${s}`),
          "",
          "**Improvements:**",
          ...data.evaluation.improvements.map((i) => `- ${i}`),
          "",
          `**Coaching Tip:** ${data.evaluation.coaching_tip}`,
          "",
          `**Sample Answer:** ${data.evaluation.sample_answer}`,
        ].join("\n");

        setMessages((prev) => [
          ...prev,
          {
            role: "coach",
            content: evalContent,
            score: data.evaluation!.score,
            category: currentQ?.category || null,
            difficulty: currentQ?.difficulty || null,
          },
        ]);
        setQuestionsAnswered((prev) => prev + 1);
      }

      setDifficulty(data.difficulty);

      if (data.session_complete) {
        setSessionComplete(true);
        setOverallScore(data.evaluation?.score || 0);
        setOverallFeedback(data.overall_feedback || null);
        setCurrentQuestion(null);
      } else if (data.next_question) {
        setCurrentQuestion(data.next_question);
        setMessages((prev) => [
          ...prev,
          {
            role: "question",
            content: data.next_question!.question,
            score: null,
            category: data.next_question!.category,
            difficulty: data.next_question!.difficulty,
          },
        ]);
      }
    } catch (err) {
      const detail = err && typeof err === "object" && "detail" in err
        ? (err as { detail: string }).detail
        : "Failed to submit answer.";
      setError(detail);
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!prepId) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-4xl px-6 py-16 text-center">
          <h2 className="text-lg font-semibold text-gray-900">No prep selected</h2>
          <p className="mt-2 text-sm text-gray-500">Go back to the interview list and select a prep.</p>
          <Link href="/interview" className="mt-4 inline-block rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
            Back to Interview Coach
          </Link>
        </div>
      </AppLayout>
    );
  }

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
            <div className="h-64 bg-gray-200 rounded" />
          </div>
        )}

        {isGenerating && !loading && (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-4">
              <svg className="h-8 w-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">Generating question bank...</h3>
            <p className="mt-2 text-sm text-gray-500">
              This usually takes 15-30 seconds. We&apos;ll start the session when ready.
            </p>
          </div>
        )}

        {error && !loading && !isGenerating && (
          <div className="text-center py-16">
            <p className="text-red-600 mb-4">{error}</p>
            <Link href="/interview" className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700">
              Back to Interview Coach
            </Link>
          </div>
        )}

        {!loading && !isGenerating && !error && !sessionId && !sessionComplete && (
          <div className="text-center py-16">
            <h2 className="text-xl font-bold text-gray-900 mb-2">Ready to Practice?</h2>
            <p className="text-sm text-gray-500 mb-6">
              {questionCount} questions across 4 categories at 3 difficulty levels.
            </p>
            <button
              type="button"
              onClick={startSession}
              disabled={isSubmitting}
              className="rounded-md bg-blue-600 px-6 py-3 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {isSubmitting ? "Starting..." : "Start Practice Session"}
            </button>
          </div>
        )}

        {sessionId && !sessionComplete && (
          <div className="rounded-lg border border-gray-200 bg-white overflow-hidden" style={{ height: "calc(100vh - 220px)" }}>
            <InterviewChat
              messages={messages}
              isLoading={isSubmitting}
              currentQuestion={currentQuestion?.question || null}
              difficulty={difficulty}
              totalQuestions={questionCount}
              questionsAnswered={questionsAnswered}
            />

            <div className="border-t border-gray-200 p-4 bg-white">
              <div className="flex gap-3">
                <textarea
                  ref={textareaRef}
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmitAnswer();
                    }
                  }}
                  placeholder="Type your answer here... (Enter to submit, Shift+Enter for new line)"
                  rows={3}
                  disabled={isSubmitting}
                  className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-none disabled:bg-gray-50"
                />
                <button
                  type="button"
                  onClick={handleSubmitAnswer}
                  disabled={isSubmitting || !answer.trim()}
                  className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
                >
                  {isSubmitting ? "..." : "Submit"}
                </button>
              </div>
            </div>
          </div>
        )}

        {sessionComplete && (
          <div className="space-y-6">
            <InterviewScoreCard
              overallScore={overallScore}
              messages={messages}
              overallFeedback={overallFeedback}
            />
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setSessionId(null);
                  setMessages([]);
                  setCurrentQuestion(null);
                  setSessionComplete(false);
                  setQuestionsAnswered(0);
                  setDifficulty(1);
                  setOverallScore(0);
                  setOverallFeedback(null);
                  setAnswer("");
                }}
                className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
              >
                Practice Again
              </button>
              <Link
                href="/interview"
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Back to List
              </Link>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
