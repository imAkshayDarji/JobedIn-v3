import { getAuthHeaders } from "@/lib/api";
import type {
  ApplySingleRequest,
  ApplySingleResponse,
  ApplyBulkRequest,
  ApplyBulkResponse,
  ApplyStatusResponse,
  ApplyBulkStatusResponse,
  ApplySSEEvent,
} from "@/types/apply";

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
}

const TERMINAL_STATUSES = new Set(["applied", "applied_with_issues", "manual_required", "failed", "rejected", "withdrawn"]);

export async function applySingle(applicationId: string): Promise<ApplySingleResponse> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}/api/apply/single`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify({ application_id: applicationId } satisfies ApplySingleRequest),
  });

  if (!response.ok) {
    const error = { status: response.status, message: response.statusText };
    try {
      const body = await response.json();
      error.message = body.detail ?? JSON.stringify(body);
    } catch {
      error.message = await response.text();
    }
    throw error;
  }

  return response.json() as Promise<ApplySingleResponse>;
}

export async function applyBulk(applicationIds: string[]): Promise<ApplyBulkResponse> {
  if (applicationIds.length === 0 || applicationIds.length > 10) {
    throw { status: 400, message: "Must select between 1 and 10 applications." };
  }

  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}/api/apply/bulk`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
    body: JSON.stringify({ application_ids: applicationIds } satisfies ApplyBulkRequest),
  });

  if (!response.ok) {
    const error = { status: response.status, message: response.statusText };
    try {
      const body = await response.json();
      error.message = body.detail ?? JSON.stringify(body);
    } catch {
      error.message = await response.text();
    }
    throw error;
  }

  return response.json() as Promise<ApplyBulkResponse>;
}

export async function getApplyStatus(applicationId: string): Promise<ApplyStatusResponse> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}/api/apply/${applicationId}/status`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
  });

  if (!response.ok) {
    const error = { status: response.status, message: response.statusText };
    try {
      const body = await response.json();
      error.message = body.detail ?? JSON.stringify(body);
    } catch {
      error.message = await response.text();
    }
    throw error;
  }

  return response.json() as Promise<ApplyStatusResponse>;
}

export async function getBulkApplyStatus(taskId: string): Promise<ApplyBulkStatusResponse> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}/api/apply/bulk/${taskId}/status`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
    },
  });

  if (!response.ok) {
    const error = { status: response.status, message: response.statusText };
    try {
      const body = await response.json();
      error.message = body.detail ?? JSON.stringify(body);
    } catch {
      error.message = await response.text();
    }
    throw error;
  }

  return response.json() as Promise<ApplyBulkStatusResponse>;
}

function parseSSELine(line: string): ApplySSEEvent | null {
  if (!line.startsWith("data: ")) return null;
  const jsonStr = line.slice(6).trim();
  if (!jsonStr || jsonStr === "[done]") return null;
  try {
    return JSON.parse(jsonStr) as ApplySSEEvent;
  } catch {
    return null;
  }
}

export interface SSECallbacks {
  onEvent: (event: ApplySSEEvent) => void;
  onDone: () => void;
  onError: (error: Error) => void;
}

export function connectApplyStream(
  applicationId: string,
  callbacks: SSECallbacks,
  maxRetries: number = 3,
): AbortController {
  const controller = new AbortController();
  let retryCount = 0;

  async function connect(): Promise<void> {
    try {
      const authHeaders = await getAuthHeaders();
      const response = await fetch(
        `${getBaseUrl()}/api/apply/${applicationId}/stream`,
        {
          method: "GET",
          headers: {
            Accept: "text/event-stream",
            ...authHeaders,
          },
          signal: controller.signal,
        },
      );

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("No response body");
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (controller.signal.aborted) return;

          const event = parseSSELine(line);
          if (!event) continue;

          callbacks.onEvent(event);

          if (event.event === "done" || (event.status && TERMINAL_STATUSES.has(event.status))) {
            callbacks.onDone();
            return;
          }
        }
      }

      if (!controller.signal.aborted) {
        retryWithBackoff();
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      if (err instanceof Error && err.name === "AbortError") return;

      retryWithBackoff();
    }
  }

  function retryWithBackoff(): void {
    if (retryCount >= maxRetries) {
      fallbackToPolling();
      return;
    }
    retryCount++;
    const delay = Math.min(1000 * Math.pow(2, retryCount - 1), 8000);
    setTimeout(() => {
      if (!controller.signal.aborted) {
        connect();
      }
    }, delay);
  }

  async function fallbackToPolling(): Promise<void> {
    try {
      const poll = async (): Promise<void> => {
        if (controller.signal.aborted) return;

        const status = await getApplyStatus(applicationId);

        callbacks.onEvent({
          event: "status_changed",
          application_id: applicationId,
          step: status.step,
          status: status.status,
          error: status.error,
        });

        if (TERMINAL_STATUSES.has(status.status)) {
          callbacks.onEvent({
            event: "done",
            application_id: applicationId,
            step: null,
            status: status.status,
            error: null,
          });
          callbacks.onDone();
          return;
        }

        setTimeout(poll, 3000);
      };

      await poll();
    } catch (err) {
      callbacks.onError(err instanceof Error ? err : new Error("Polling failed"));
    }
  }

  connect();
  return controller;
}
