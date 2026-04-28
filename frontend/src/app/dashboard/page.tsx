"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";

interface UserProfile {
  email: string;
  id: string;
}

export default function DashboardPage() {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    async function loadUser() {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();

      if (session?.user) {
        setUser({
          email: session.user.email ?? "",
          id: session.user.id,
        });
      }

      setLoading(false);
    }

    loadUser();
  }, []);

  if (loading) {
    return (
      <AppLayout>
        <div className="mx-auto max-w-7xl px-6 py-12">
          <div className="animate-pulse">
            <div className="h-8 bg-gray-200 rounded w-1/3 mb-2" />
            <div className="h-4 bg-gray-200 rounded w-1/2" />
          </div>
        </div>
      </AppLayout>
    );
  }

  if (!user) {
    return (
      <AppLayout>
        <div className="flex min-h-[50vh] items-center justify-center">
          <p className="text-gray-500">Redirecting to login...</p>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout>
      <div className="mx-auto max-w-7xl px-6 py-12">
        <h1 className="text-3xl font-bold text-gray-900">
          Welcome, {user.email}
        </h1>
        <p className="mt-2 text-gray-600">
          Your dashboard is ready. Start exploring job opportunities.
        </p>

        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Link href="/resumes" className="block">
            <div className="rounded-lg border border-gray-200 bg-white p-6 hover:border-blue-300 hover:shadow-sm transition-all">
              <h3 className="font-semibold text-gray-900">Resumes</h3>
              <p className="mt-1 text-sm text-gray-500">
                Manage and optimize your resumes
              </p>
            </div>
          </Link>
          <Link href="/jobs" className="block">
            <div className="rounded-lg border border-gray-200 bg-white p-6 hover:border-blue-300 hover:shadow-sm transition-all">
              <h3 className="font-semibold text-gray-900">Jobs</h3>
              <p className="mt-1 text-sm text-gray-500">
                Browse AI-matched opportunities
              </p>
            </div>
          </Link>
          <div className="rounded-lg border border-gray-200 bg-white p-6 opacity-60">
            <h3 className="font-semibold text-gray-900">Applications</h3>
            <p className="mt-1 text-sm text-gray-500">
              Track your job applications
            </p>
            <p className="mt-2 text-xs text-gray-400">Coming soon</p>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
