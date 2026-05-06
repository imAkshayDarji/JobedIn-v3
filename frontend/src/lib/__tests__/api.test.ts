import { beforeEach, describe, expect, it, vi } from "vitest";

import { api, getAuthHeaders, type ApiError } from "../api";

vi.mock("@clerk/nextjs/server", () => ({
  auth: () => ({
    getToken: vi.fn().mockResolvedValue("test-token-123"),
    userId: "user_test_123",
  }),
}));
vi.mock("@sentry/nextjs", () => ({
  captureException: vi.fn(),
  addBreadcrumb: vi.fn(),
  setContext: vi.fn(),
}));
vi.mock("sonner", () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    warning: vi.fn(),
    info: vi.fn(),
  },
  Toaster: () => null,
}));

describe("getAuthHeaders", () => {
  it("returns Authorization header with Bearer token", async () => {
    const headers = await getAuthHeaders();
    expect(headers).toEqual({ Authorization: "Bearer test-token-123" });
  });
});

describe("handleResponse (via api.get)", () => {
  it("returns parsed JSON on 200", async () => {
    const data = { id: 1, name: "test" };
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(data), { status: 200, statusText: "OK" }),
    );

    const result = await api.get("/test");
    expect(result).toEqual(data);
  });

  it("throws with Unauthorized on 401", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Invalid token" }), {
        status: 401,
        statusText: "Unauthorized",
      }),
    );

    await expect(api.get("/test")).rejects.toEqual(
      expect.objectContaining({ status: 401 }),
    );
  });

  it("throws with rate limit info on 429", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Too many requests" }), {
        status: 429,
        statusText: "Too Many Requests",
      }),
    );

    await expect(api.get("/test")).rejects.toEqual(
      expect.objectContaining({ status: 429 }),
    );
  });

  it("throws on 500", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Internal error" }), {
        status: 500,
        statusText: "Internal Server Error",
      }),
    );

    await expect(api.get("/test")).rejects.toEqual(
      expect.objectContaining({ status: 500 }),
    );
  });
});

describe("api.get", () => {
  it("calls fetch with correct URL and headers", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );

    await api.get("/jobs");

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/jobs"),
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer test-token-123",
        }),
      }),
    );
  });
});

describe("api.post", () => {
  it("calls fetch with POST method and JSON body", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockResolvedValue(
        new Response(JSON.stringify({ ok: true }), { status: 200 }),
      );

    const payload = { title: "Engineer", company: "Acme" };
    await api.post("/jobs", payload);

    expect(fetchSpy).toHaveBeenCalledWith(
      expect.stringContaining("/jobs"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
        headers: expect.objectContaining({
          "Content-Type": "application/json",
          Authorization: "Bearer test-token-123",
        }),
      }),
    );
  });
});
