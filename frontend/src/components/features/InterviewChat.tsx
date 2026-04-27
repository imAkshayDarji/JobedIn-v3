"use client";

import { useEffect, useRef } from "react";
import type { SessionMessage } from "@/types/interview";

interface InterviewChatProps {
  messages: SessionMessage[];
  isLoading: boolean;
  currentQuestion: string | null;
  difficulty: number;
  totalQuestions: number;
  questionsAnswered: number;
}

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

function getDifficultyColor(d: number): string {
  switch (d) {
    case 1:
      return "bg-green-500";
    case 2:
      return "bg-yellow-500";
    case 3:
      return "bg-red-500";
    default:
      return "bg-gray-500";
  }
}

export function InterviewChat({
  messages,
  isLoading,
  currentQuestion,
  difficulty,
  totalQuestions,
  questionsAnswered,
}: InterviewChatProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-gray-700">
            Difficulty: {difficulty}/3
          </span>
          <div className="flex gap-1">
            {[1, 2, 3].map((level) => (
              <div
                key={level}
                className={`w-3 h-3 rounded-full ${level <= difficulty ? getDifficultyColor(difficulty) : "bg-gray-200"}`}
              />
            ))}
          </div>
        </div>
        <span className="text-sm text-gray-500">
          Question {questionsAnswered + 1} of {totalQuestions}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`rounded-lg border p-4 ${getRoleStyles(msg.role)}`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-gray-600 uppercase">
                {getRoleLabel(msg.role)}
              </span>
              {msg.score !== null && msg.score !== undefined && (
                <span className="text-xs font-medium text-gray-500">
                  Score: {msg.score}/10
                </span>
              )}
              {msg.difficulty !== null && msg.difficulty !== undefined && (
                <span
                  className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${getDifficultyColor(msg.difficulty)} text-white`}
                >
                  Level {msg.difficulty}
                </span>
              )}
            </div>
            <div className="text-sm text-gray-800 whitespace-pre-wrap">
              {msg.content}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-4">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-2 h-2 bg-blue-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
            <span className="text-sm text-blue-600">Coach is evaluating your answer...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
