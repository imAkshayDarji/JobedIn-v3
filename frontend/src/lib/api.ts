import { createClient } from "@/lib/supabase/client";

interface ApiError {
  status: number;
  message: string;
  detail?: string;
}

interface RequestOptions {
  headers?: Record<string, string>;
  signal?: AbortSignal;
}

export async function getAuthHeaders(): Promise<Record<string, string>> {
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

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error: ApiError = {
      status: response.status,
      message: response.statusText,
    };

    try {
      const body = await response.json();
      error.detail = body.detail ?? JSON.stringify(body);
    } catch {
      error.detail = await response.text();
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
