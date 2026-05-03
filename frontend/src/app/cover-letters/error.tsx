"use client";

import { ErrorDisplay } from "@/components/ui/ErrorDisplay";

export default function CoverLettersError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorDisplay error={error} reset={reset} title="Cover Letters Error" />;
}
