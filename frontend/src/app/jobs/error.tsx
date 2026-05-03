"use client";

import { ErrorDisplay } from "@/components/ui/ErrorDisplay";

export default function JobsError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorDisplay error={error} reset={reset} title="Jobs Error" />;
}
