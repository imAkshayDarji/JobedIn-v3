import * as Sentry from "@sentry/nextjs";
import { toast } from "sonner";

import { createClient } from "@/lib/supabase/client";

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

export async function getAuthHeaders(): Promise<Record<string, string>> {
  // Auth bypass — send a dev header so the backend knows we're in bypass mode
  if (process.env.NEXT_PUBLIC_BYPASS_AUTH === "true") {
    return { "X-Dev-Bypass": "true" };
  }

  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();

  if (session?.access_token) {
    return { Authorization: `Bearer ${session.access_token}` };
  }

  return {};
}

function getBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
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
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    signal: options?.signal,
  });
  return handleResponse<T>(response);
}

async function post<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function put<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function patch<T>(
  path: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  return handleResponse<T>(response);
}

async function del<T>(path: string, options?: RequestOptions): Promise<T> {
  const authHeaders = await getAuthHeaders();
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...options?.headers,
    },
  });
  return handleResponse<T>(response);
}

export const api = { get, post, put, patch, delete: del };
export type { ApiError };
