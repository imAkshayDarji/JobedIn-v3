"use client";

import { useCallback, useEffect, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { ActivityFeed } from "@/components/features/ActivityFeed";
import { QuickActions } from "@/components/features/QuickActions";
import { StatCard } from "@/components/features/StatCard";
import { getDashboard } from "@/lib/api/dashboard";
import type { DashboardResponse } from "@/types/dashboard";
import type { ApiError } from "@/lib/api";

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const result = await getDashboard(signal);
      setData(result);
    } catch (err) {
      if (err instanceof DOMException && err.name === "AbortError") return;
      const apiErr = err as ApiError | Error;
      setError(
        apiErr && "detail" in apiErr
          ? apiErr.detail ?? "Failed to load dashboard"
          : apiErr.message ?? "Failed to load dashboard",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    fetchData(controller.signal);
    return () => controller.abort();
  }, [fetchData]);

  const firstName = data?.profile?.first_name ?? "Welcome";

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-8">
        {loading ? (
          <DashboardSkeleton />
        ) : error ? (
          <ErrorState message={error} onRetry={() => fetchData()} />
        ) : data ? (
          <>
            <Header firstName={firstName} />
            <StatCards stats={data.stats} />
            {isEmptyUser(data.stats) ? (
              <EmptyState />
            ) : (
              <>
                <Section title="Quick Actions">
                  <QuickActions />
                </Section>
                <Section title="Recent Activity">
                  <ActivityFeed items={data.recent_activity} />
                </Section>
              </>
            )}
          </>
        ) : null}
      </div>
    </AppLayout>
  );
}

function Header({ firstName }: { firstName: string }) {
  return (
    <div className="mb-8">
      <h1 className="text-3xl font-bold text-gray-900">
        Welcome, {firstName}
      </h1>
      <p className="mt-1 text-gray-600">
        Your job search dashboard
      </p>
    </div>
  );
}

function StatCards({ stats }: { stats: DashboardResponse["stats"] }) {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-8">
      <StatCard
        label="Jobs Matched"
        value={stats.jobs_matched}
        subtitle={
          stats.high_match_count > 0
            ? `${stats.high_match_count} high matches (70+)`
            : undefined
        }
        color="blue"
        progress={stats.avg_match_score ?? undefined}
        href="/jobs"
      />
      <StatCard
        label="Applications"
        value={stats.applications_count}
        subtitle={
          Object.entries(stats.applications_by_status)
            .map(([s, c]) => `${s}: ${c}`)
            .join(", ") || undefined
        }
        color="green"
        href="/applications"
      />
      <StatCard
        label="Resumes"
        value={stats.resumes_count}
        subtitle={
          stats.resumes_completed > 0
            ? `${stats.resumes_completed} completed`
            : undefined
        }
        color="purple"
        href="/resumes"
      />
      <StatCard
        label="Cover Letters"
        value={stats.cover_letters_count}
        color="teal"
      />
      <StatCard
        label="Practice Sessions"
        value={stats.interview_sessions_count}
        subtitle={
          stats.interview_sessions_completed > 0
            ? `${stats.interview_sessions_completed} completed`
            : undefined
        }
        color="yellow"
        href="/interview"
      />
      <StatCard
        label="Avg ATS Score"
        value={stats.avg_ats_score !== null ? `${Math.round(stats.avg_ats_score)}%` : null}
        subtitle={stats.avg_ats_score === null ? "No data yet" : undefined}
        color={stats.avg_ats_score !== null && stats.avg_ats_score >= 70 ? "green" : "gray"}
        progress={stats.avg_ats_score ?? undefined}
        href="/resumes"
      />
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-8">
      <h2 className="text-lg font-semibold text-gray-900 mb-3">{title}</h2>
      {children}
    </div>
  );
}

function isEmptyUser(stats: DashboardResponse["stats"]): boolean {
  return stats.jobs_matched === 0 && stats.resumes_count === 0;
}

function EmptyState() {
  return (
    <div className="rounded-lg border-2 border-dashed border-gray-300 p-8 text-center">
      <h3 className="text-lg font-semibold text-gray-900 mb-2">
        Get started with your job search
      </h3>
      <p className="text-sm text-gray-600 mb-6">
        Complete these steps to unlock the full power of JobedIn
      </p>
      <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
        <a
          href="/onboarding"
          className="inline-flex items-center rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-blue-700 transition-colors"
        >
          1. Complete Profile
        </a>
        <a
          href="/jobs"
          className="inline-flex items-center rounded-lg bg-white border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          2. Discover Jobs
        </a>
        <a
          href="/resumes/generate"
          className="inline-flex items-center rounded-lg bg-white border border-gray-300 px-5 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          3. Generate Resume
        </a>
      </div>
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
      <p className="text-sm font-medium text-red-800 mb-3">{message}</p>
      <button
        type="button"
        onClick={onRetry}
        className="inline-flex items-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
      >
        Retry
      </button>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="mb-8">
        <div className="h-8 bg-gray-200 rounded w-1/3 mb-2" />
        <div className="h-4 bg-gray-200 rounded w-1/2" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 mb-8">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-24 rounded-lg bg-gray-200" />
        ))}
      </div>
      <div className="flex gap-3 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 w-32 rounded-lg bg-gray-200" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-12 rounded-lg bg-gray-200" />
        ))}
      </div>
    </div>
  );
}
