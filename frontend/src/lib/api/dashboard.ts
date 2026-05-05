import { api } from "@/lib/api";
import type { DashboardResponse } from "@/types/dashboard";

export async function getDashboard(
  signal?: AbortSignal,
): Promise<DashboardResponse> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 30_000);

  const combinedSignal = signal
    ? AbortSignal.any([signal, controller.signal])
    : controller.signal;

  try {
    return await api.get<DashboardResponse>("/api/dashboard", {
      signal: combinedSignal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("Dashboard data took too long to load. Please try again.");
    }
    throw err;
  } finally {
    clearTimeout(timeoutId);
  }
}
