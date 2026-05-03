"use client";

import { ErrorDisplay } from "@/components/ui/ErrorDisplay";

export default function ResumesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorDisplay error={error} reset={reset} title="Resumes Error" />;
}
