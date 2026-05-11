import * as Sentry from "@sentry/nextjs";
import { toast } from "sonner";

interface ClerkLike {
  loaded?: boolean;
  session?: {
    getToken: (
      options?: { template?: string; skipCache?: boolean },
    ) => Promise<string | null | undefined>;
  };
}

interface ApiError {
  status: number;
  message: string;
  detail?: string;
  code?: string;
}

interface RequestOptions {
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

async function getBrowserClerkAuthHeaders(
  skipCache = false,
): Promise<Record<string, string>> {
  if (typeof window === "undefined") {
    return {};
  }

  const clerk = (window as Window & { Clerk?: ClerkLike }).Clerk;
  if (!clerk?.session) {
    return {};
  }

  try {
    const token = await clerk.session.getToken(
      skipCache ? { skipCache: true } : undefined,
    );
    if (token) {
      return { Authorization: `Bearer ${token}` };
    }
  } catch {
    return {};
  }

  return {};
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH === "true") {
    return { "X-Dev-Bypass": "true" };
  }

  return getBrowserClerkAuthHeaders(false);
}

async function resolveAuthHeaders(forceFreshToken: boolean): Promise<Record<string, string>> {
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH === "true") {
    return { "X-Dev-Bypass": "true" };
  }

  return getBrowserClerkAuthHeaders(forceFreshToken);
}

export function getApiBaseUrl(): string {
  const raw = process.env.NEXT_PUBLIC_API_URL;
  if (typeof raw === "string" && raw.trim() !== "") {
    return raw.replace(/\/$/, "");
  }
  return "http://localhost:8000";
}

async function fetchWithAuthRetry(
  path: string,
  init: RequestInit,
): Promise<Response> {
  const url = `${getApiBaseUrl()}${path}`;

  async function doFetch(forceFreshToken: boolean): Promise<Response> {
    const auth = await resolveAuthHeaders(forceFreshToken);
    const headers: Record<string, string> = {
      ...auth,
      ...(init.headers as Record<string, string> | undefined),
    };
    if (!(init.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    return fetch(url, {
      ...init,
      headers,
    });
  }

  let response = await doFetch(false);
  if (
    response.status === 401 &&
    typeof window !== "undefined" &&
    process.env.NEXT_PUBLIC_BYPASS_AUTH !== "true"
  ) {
    const refreshed = await resolveAuthHeaders(true);
    if (refreshed.Authorization) {
      response = await doFetch(true);
    }
  }

  return response;
}

/** Authenticated fetch with one Clerk token refresh retry on 401. */
export async function authenticatedFetch(
  path: string,
  init: RequestInit,
): Promise<Response> {
  return fetchWithAuthRetry(path, init);
}

function handle401(): void {
  toast.error("Session expired. Please sign in again.");
  const redirectPath = window.location.pathname;
  window.location.href = `/auth/login?redirect=${encodeURIComponent(redirectPath)}`;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: response.statusText,
    };

    try {
      const body = await response.json();
      const rawDetail = body.detail ?? body.error?.message ?? JSON.stringify(body);
      error.detail = typeof rawDetail === "string"
        ? rawDetail
        : JSON.stringify(rawDetail);
      error.code = body.error?.code;
    } catch {
      error.detail = await response.text();
    }

    Sentry.addBreadcrumb({
      category: "api",
      message: `${response.status} ${response.url}`,
      level: response.status >= 500 ? "error" : "warning",
      data: {
        status: response.status,
        url: response.url,
      },
    });

    if (response.status === 401) {
      handle401();
      throw error;
    }

    if (response.status === 403) {
      toast.error("You do not have permission to perform this action.");
    } else if (response.status === 429) {
      toast.warning("Too many requests. Please slow down and try again.");
    } else if (response.status >= 500) {
      Sentry.captureException(new Error(`API ${response.status}: ${error.detail}`));
      toast.error("Something went wrong. Please try again later.");
    }

    throw error;
  }

  return response.json() as Promise<T>;
}

async function get<T>(path: string, options?: RequestOptions): Promise<T> {
  const response = await fetchWithAuthRetry(path, {
    method: "GET",
    headers: options?.headers,
    signal: options?.signal,
  });
  return handleResponse<T>(response);
}

async function post<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const response = await fetchWithAuthRetry(path, {
    method: "POST",
    headers: options?.headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function put<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const response = await fetchWithAuthRetry(path, {
    method: "PUT",
    headers: options?.headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function patch<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const response = await fetchWithAuthRetry(path, {
    method: "PATCH",
    headers: options?.headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function del<T>(path: string, options?: RequestOptions): Promise<T> {
  const response = await fetchWithAuthRetry(path, {
    method: "DELETE",
    headers: options?.headers,
  });
  return handleResponse<T>(response);
}

export const api = { get, post, put, patch, delete: del };
export type { ApiError };
