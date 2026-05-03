import { describe, expect, it, vi } from "vitest";

import { render, screen, fireEvent } from "@/test/utils";

import { ErrorDisplay } from "../ErrorDisplay";

const mockError = new Error("Test error message");
mockError.digest = "abc123";

describe("ErrorDisplay", () => {
  it("renders error heading", () => {
    render(<ErrorDisplay error={mockError} reset={vi.fn()} />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders custom title when provided", () => {
    render(
      <ErrorDisplay
        error={mockError}
        reset={vi.fn()}
        title="Custom Error Title"
      />,
    );
    expect(screen.getByText("Custom Error Title")).toBeInTheDocument();
  });

  it("shows Try Again button", () => {
    render(<ErrorDisplay error={mockError} reset={vi.fn()} />);
    expect(
      screen.getByRole("button", { name: "Try Again" }),
    ).toBeInTheDocument();
  });

  it("calls reset callback when Try Again clicked", () => {
    const reset = vi.fn();
    render(<ErrorDisplay error={mockError} reset={reset} />);
    fireEvent.click(screen.getByRole("button", { name: "Try Again" }));
    expect(reset).toHaveBeenCalledTimes(1);
  });
});
