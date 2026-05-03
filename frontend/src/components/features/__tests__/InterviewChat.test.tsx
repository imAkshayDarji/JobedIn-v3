import { describe, expect, it, beforeAll, vi } from "vitest";

import type { SessionMessage } from "@/types/interview";

import { render, screen } from "@/test/utils";

import { InterviewChat } from "../InterviewChat";

const baseMessages: SessionMessage[] = [
  {
    role: "question",
    content: "Tell me about a challenging project you worked on.",
    score: null,
    category: "behavioral",
    difficulty: 2,
  },
  {
    role: "user",
    content: "I led a migration from monolith to microservices.",
    score: null,
    category: null,
    difficulty: null,
  },
  {
    role: "coach",
    content: "Good answer! Consider adding specific metrics.",
    score: 8,
    category: null,
    difficulty: null,
  },
];

const defaultProps = {
  messages: baseMessages,
  isLoading: false,
  currentQuestion: null,
  difficulty: 2,
  totalQuestions: 5,
  questionsAnswered: 1,
};

describe("InterviewChat", () => {
  beforeAll(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  it("renders difficulty indicator and question progress", () => {
    render(<InterviewChat {...defaultProps} />);

    expect(screen.getByText("Difficulty: 2/3")).toBeInTheDocument();
    expect(screen.getByText("Question 2 of 5")).toBeInTheDocument();
  });

  it("renders messages with correct role labels", () => {
    render(<InterviewChat {...defaultProps} />);

    expect(screen.getByText("Interviewer")).toBeInTheDocument();
    expect(screen.getByText("You")).toBeInTheDocument();
    expect(screen.getByText("Coach")).toBeInTheDocument();
    expect(
      screen.getByText("Tell me about a challenging project you worked on."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("I led a migration from monolith to microservices."),
    ).toBeInTheDocument();
  });

  it("shows score on messages that have a score", () => {
    render(<InterviewChat {...defaultProps} />);

    expect(screen.getByText("Score: 8/10")).toBeInTheDocument();
  });

  it("shows loading indicator when isLoading is true", () => {
    render(<InterviewChat {...defaultProps} isLoading={true} />);

    expect(
      screen.getByText("Coach is evaluating your answer..."),
    ).toBeInTheDocument();
  });

  it("does not show loading indicator when isLoading is false", () => {
    render(<InterviewChat {...defaultProps} isLoading={false} />);

    expect(
      screen.queryByText("Coach is evaluating your answer..."),
    ).not.toBeInTheDocument();
  });
});
