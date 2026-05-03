"use client";

import { ErrorDisplay } from "@/components/ui/ErrorDisplay";

export default function InterviewError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return <ErrorDisplay error={error} reset={reset} title="Interview Error" />;
}
