import { describe, expect, it, vi } from "vitest";

import { render, screen, fireEvent, waitFor } from "@/test/utils";

import { ApplyModal } from "../ApplyModal";

vi.mock("@/lib/api/apply", () => ({
  applySingle: vi.fn(),
  connectApplyStream: vi.fn(() => new AbortController()),
  getApplyDetectionStatus: vi.fn(),
}));

import { applySingle, connectApplyStream } from "@/lib/api/apply";

const mockApplySingle = vi.mocked(applySingle);
const mockConnectApplyStream = vi.mocked(connectApplyStream);

function applyingResponse() {
  return {
    application_id: "app-123",
    task_id: "task-1",
    message: "Started",
    phase: "applying" as const,
  };
}

const defaultProps = {
  applicationId: "app-123",
  jobTitle: "Senior Frontend Engineer",
  companyName: "Acme Corp",
  onClose: vi.fn(),
  onCompleted: vi.fn(),
};

describe("ApplyModal", () => {
  it("renders Start Auto Apply button with job title and company name", () => {
    render(<ApplyModal {...defaultProps} />);

    expect(screen.getByText("Start Auto Apply")).toBeInTheDocument();
    expect(screen.getByText("Auto Apply")).toBeInTheDocument();
    expect(screen.getAllByText("Senior Frontend Engineer").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Acme Corp").length).toBeGreaterThan(0);
  });

  it("shows close confirmation when clicking close during active apply", async () => {
    mockApplySingle.mockResolvedValueOnce(applyingResponse());

    render(<ApplyModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Start Auto Apply"));

    await waitFor(() => {
      expect(mockApplySingle).toHaveBeenCalledWith("app-123");
    });

    expect(screen.queryByText("Close Anyway")).not.toBeInTheDocument();

    const header = screen.getByText("Auto Apply").closest(".sticky");
    const closeButton = header!.querySelector("button")!;
    fireEvent.click(closeButton);

    expect(screen.getByText("Close Anyway")).toBeInTheDocument();
    expect(screen.getByText("Keep Watching")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close Anyway"));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it("displays error state with retry button when applySingle throws", async () => {
    mockApplySingle.mockRejectedValueOnce(new Error("Network timeout"));

    render(<ApplyModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Start Auto Apply"));

    await waitFor(() => {
      expect(screen.getByText("Error")).toBeInTheDocument();
    });

    expect(screen.getByText("Network timeout")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("displays success result on applied status event", async () => {
    let capturedCallbacks: import("@/lib/api/apply").SSECallbacks | null = null;

    mockApplySingle.mockResolvedValueOnce(applyingResponse());

    mockConnectApplyStream.mockImplementationOnce(
      (_appId: string, callbacks: import("@/lib/api/apply").SSECallbacks) => {
        capturedCallbacks = callbacks;
        return new AbortController();
      },
    );

    render(<ApplyModal {...defaultProps} />);

    fireEvent.click(screen.getByText("Start Auto Apply"));

    await waitFor(() => {
      expect(mockApplySingle).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(capturedCallbacks).not.toBeNull();
    });

    capturedCallbacks!.onEvent({
      event: "progress",
      application_id: "app-123",
      step: "submitting",
      steps_completed: ["load_profile"],
      status: "applying",
      error: null,
    });

    capturedCallbacks!.onEvent({
      event: "done",
      application_id: "app-123",
      step: null,
      status: "applied",
      error: null,
    });

    await waitFor(() => {
      expect(
        screen.getByText("Application submitted successfully"),
      ).toBeInTheDocument();
    });
  });
});
