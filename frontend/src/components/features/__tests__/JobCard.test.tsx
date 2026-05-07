import { describe, expect, it } from "vitest";

import type { JobListItem } from "@/types/job";

import { render, screen } from "@/test/utils";

import { JobCard } from "../JobCard";

const baseJob: JobListItem = {
  id: "job-1",
  title: "Senior Frontend Engineer",
  company: "Acme Corp",
  location: "San Francisco, CA",
  source: "linkedin",
  source_url: "https://linkedin.com/jobs/1",
  salary_min: 120000,
  salary_max: 180000,
  salary_currency: "USD",
  experience_level: "Senior",
  job_type: "Full-time",
  remote_policy: "remote",
  scraped_at: "2025-01-01T00:00:00Z",
  created_at: "2025-01-01T00:00:00Z",
  match_score: 85,
  is_saved: false,
};

describe("JobCard", () => {
  it("renders job title and company name", () => {
    render(<JobCard job={baseJob} />);
    expect(screen.getByText("Senior Frontend Engineer")).toBeInTheDocument();
    expect(screen.getByText("Acme Corp")).toBeInTheDocument();
  });

  it("shows match score badge", () => {
    render(<JobCard job={baseJob} />);
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("Match")).toBeInTheDocument();
  });

  it("shows source badge", () => {
    render(<JobCard job={baseJob} />);
    expect(screen.getByText("linkedin")).toBeInTheDocument();
  });

  it("shows salary range when provided", () => {
    render(<JobCard job={baseJob} />);
    expect(screen.getByText(/\$120,000/)).toBeInTheDocument();
    expect(screen.getByText(/\$180,000/)).toBeInTheDocument();
  });

  it("shows not scored when match_score is null", () => {
    const job = { ...baseJob, match_score: null };
    render(<JobCard job={job} />);
    expect(screen.getByText("Not scored")).toBeInTheDocument();
  });

  it("links to correct job detail URL", () => {
    render(<JobCard job={baseJob} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/jobs/job-1");
  });
});
