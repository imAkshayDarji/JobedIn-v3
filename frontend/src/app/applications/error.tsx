"use client";

import { ErrorDisplay } from "@/components/ui/ErrorDisplay";

export default function ApplicationsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorDisplay error={error} reset={reset} title="Applications Error" />;
}
