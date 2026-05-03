import { describe, expect, it, vi } from "vitest";

import type { ApplicationListItem } from "@/types/application";

import { render, screen, fireEvent } from "@/test/utils";

import { ApplicationCard } from "../ApplicationCard";

const baseApplication: ApplicationListItem = {
  id: "app-1",
  status: "applied",
  applied_at: "2025-01-01T00:00:00Z",
  notes: null,
  created_at: "2025-01-01T00:00:00Z",
  updated_at: "2025-01-01T00:00:00Z",
  job: {
    id: "job-1",
    title: "Backend Engineer",
    company: "TechCo",
    location: "New York, NY",
    source: "adzuna",
    source_url: null,
    salary_min: 100000,
    salary_max: 150000,
    remote_policy: null,
    experience_level: "Mid",
  },
  match_score: 72,
  resume_id: null,
  cover_letter_id: null,
  interview_prep_id: null,
};

describe("ApplicationCard", () => {
  it("renders job title and company", () => {
    render(
      <ApplicationCard application={baseApplication} onClick={vi.fn()} />,
    );
    expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
    expect(screen.getByText("TechCo")).toBeInTheDocument();
  });

  it("shows status badge", () => {
    render(
      <ApplicationCard application={baseApplication} onClick={vi.fn()} />,
    );
    expect(screen.getByText("applied")).toBeInTheDocument();
  });

  it("shows match score", () => {
    render(
      <ApplicationCard application={baseApplication} onClick={vi.fn()} />,
    );
    expect(screen.getByText("72%")).toBeInTheDocument();
  });

  it("calls onClick when in non-selectable mode", () => {
    const onClick = vi.fn();
    render(
      <ApplicationCard application={baseApplication} onClick={onClick} />,
    );
    fireEvent.click(screen.getByText("Backend Engineer"));
    expect(onClick).toHaveBeenCalled();
  });

  it("calls onSelect when in selectable mode", () => {
    const onSelect = vi.fn();
    render(
      <ApplicationCard
        application={baseApplication}
        onClick={vi.fn()}
        selectable
        onSelect={onSelect}
      />,
    );
    fireEvent.click(screen.getByText("Backend Engineer"));
    expect(onSelect).toHaveBeenCalled();
  });

  it("shows artifact dots for resume/cover_letter/interview_prep", () => {
    const app = {
      ...baseApplication,
      resume_id: "res-1",
      cover_letter_id: "cl-1",
      interview_prep_id: "ip-1",
    };
    render(<ApplicationCard application={app} onClick={vi.fn()} />);
    expect(screen.getByTitle("Resume linked")).toBeInTheDocument();
    expect(screen.getByTitle("Cover letter linked")).toBeInTheDocument();
    expect(screen.getByTitle("Interview prep linked")).toBeInTheDocument();
  });

  it("does not show artifact dots when IDs are null", () => {
    render(
      <ApplicationCard application={baseApplication} onClick={vi.fn()} />,
    );
    expect(screen.queryByTitle("Resume linked")).not.toBeInTheDocument();
    expect(
      screen.queryByTitle("Cover letter linked"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTitle("Interview prep linked"),
    ).not.toBeInTheDocument();
  });
});
