"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { AppLayout } from "@/components/layout/AppLayout";
import { generateCoverLetterManual, getCoverLetterStatus } from "@/lib/api/cover-letters";

const POLL_INTERVAL_MS = 3000;
const MAX_POLL_ATTEMPTS = 80;

type Tone = "professional" | "casual" | "enthusiastic";

const TONE_OPTIONS: { value: Tone; label: string; description: string }[] = [
  { value: "professional", label: "Professional", description: "Formal and polished" },
  { value: "casual", label: "Casual", description: "Friendly and approachable" },
  { value: "enthusiastic", label: "Enthusiastic", description: "Energetic and passionate" },
];

export default function GenerateCoverLetterPage() {
  const router = useRouter();
  const [jobDescription, setJobDescription] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [jobTitle, setJobTitle] = useState("");
  const [tone, setTone] = useState<Tone>("professional");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [coverLetterId, setCoverLetterId] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setError(null);
    setLoading(true);

    try {
      const result = await generateCoverLetterManual({
        job_description: jobDescription,
        company_name: companyName || undefined,
        job_title: jobTitle || undefined,
        tone,
      });

      setCoverLetterId(result.cover_letter_id);

      if (result.status === "completed") {
        router.push(`/cover-letters/${result.cover_letter_id}`);
        return;
      }

      let attempts = 0;
      const poll = async () => {
        try {
          const status = await getCoverLetterStatus(result.cover_letter_id);
          if (status.status === "completed") {
            router.push(`/cover-letters/${result.cover_letter_id}`);
            return;
          }
          if (status.status === "failed") {
            setError("Cover letter generation failed. Please try again.");
            setLoading(false);
            return;
          }
          attempts++;
          if (attempts >= MAX_POLL_ATTEMPTS) {
            setError("Cover letter generation is taking too long. Check your cover letters list.");
            setLoading(false);
            return;
          }
          setTimeout(poll, POLL_INTERVAL_MS);
        } catch {
          attempts++;
          if (attempts >= MAX_POLL_ATTEMPTS) {
            setError("Failed to check generation status. Please check your cover letters list.");
            setLoading(false);
            return;
          }
          setTimeout(poll, POLL_INTERVAL_MS);
        }
      };

      setTimeout(poll, POLL_INTERVAL_MS);
    } catch (err: unknown) {
      const message =
        err && typeof err === "object" && "detail" in err
          ? (err as { detail: string }).detail
          : "Failed to start cover letter generation. Please try again.";
      setError(message);
      setLoading(false);
    }
  }

  const descriptionLength = jobDescription.length;
  const isDescriptionValid = descriptionLength >= 50 && descriptionLength <= 10000;

  return (
    <AppLayout>
      <div className="mx-auto max-w-3xl px-6 py-8">
        <div className="mb-8">
          <Link
            href="/cover-letters"
            className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1"
          >
            <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
            </svg>
            Back to Cover Letters
          </Link>
          <h1 className="text-2xl font-bold text-gray-900 mt-2">
            Generate Cover Letter
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Paste a job description and we&apos;ll create a tailored cover letter for you.
          </p>
        </div>

        {loading ? (
          <div className="text-center py-16">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 mb-4">
              <svg className="h-8 w-8 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900">
              Generating your cover letter...
            </h3>
            <p className="mt-2 text-sm text-gray-500">
              This usually takes 15-60 seconds. We&apos;ll redirect you when it&apos;s ready.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label
                htmlFor="job_description"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Job Description <span className="text-red-500">*</span>
              </label>
              <textarea
                id="job_description"
                value={jobDescription}
                onChange={(e) => setJobDescription(e.target.value)}
                rows={10}
                placeholder="Paste the full job description here..."
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 resize-y"
                required
                minLength={50}
                maxLength={10000}
              />
              <div className="mt-1 flex justify-between text-xs text-gray-400">
                <span>Minimum 50 characters</span>
                <span className={descriptionLength > 9500 ? "text-red-500" : ""}>
                  {descriptionLength.toLocaleString()} / 10,000
                </span>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label
                  htmlFor="company_name"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Company Name <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  id="company_name"
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g., Google"
                  maxLength={200}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label
                  htmlFor="job_title"
                  className="block text-sm font-medium text-gray-700 mb-1"
                >
                  Job Title <span className="text-gray-400">(optional)</span>
                </label>
                <input
                  id="job_title"
                  type="text"
                  value={jobTitle}
                  onChange={(e) => setJobTitle(e.target.value)}
                  placeholder="e.g., Senior Backend Engineer"
                  maxLength={200}
                  className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 placeholder-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>

            <fieldset>
              <legend className="block text-sm font-medium text-gray-700 mb-2">
                Tone
              </legend>
              <div className="grid gap-3 sm:grid-cols-3">
                {TONE_OPTIONS.map((option) => (
                  <label
                    key={option.value}
                    className={`relative flex cursor-pointer rounded-lg border px-4 py-3 transition-colors ${
                      tone === option.value
                        ? "border-blue-500 bg-blue-50 ring-1 ring-blue-500"
                        : "border-gray-200 bg-white hover:border-gray-300"
                    }`}
                  >
                    <input
                      type="radio"
                      name="tone"
                      value={option.value}
                      checked={tone === option.value}
                      onChange={() => setTone(option.value)}
                      className="sr-only"
                    />
                    <div>
                      <span className="block text-sm font-medium text-gray-900">
                        {option.label}
                      </span>
                      <span className="block text-xs text-gray-500 mt-0.5">
                        {option.description}
                      </span>
                    </div>
                  </label>
                ))}
              </div>
            </fieldset>

            {error && (
              <div className="rounded-md bg-red-50 p-4">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <div className="flex items-center gap-3">
              <button
                type="submit"
                disabled={!isDescriptionValid || loading}
                className="rounded-md bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                Generate Cover Letter
              </button>
              <Link
                href="/cover-letters"
                className="rounded-md border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </Link>
            </div>
          </form>
        )}
      </div>
    </AppLayout>
  );
}
