"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { generateCoverLetter, listCoverLetters } from "@/lib/api/cover-letters";
import { generateResume, getResume, listResumes } from "@/lib/api/resumes";
import { authenticatedFetch } from "@/lib/api";
import { CoverLetterDownloadButton } from "@/components/features/CoverLetterDownloadButton";
import { ResumeDownloadButton } from "@/components/features/ResumeDownloadButton";
import type { CoverLetterListItem } from "@/types/cover-letter";
import type { ResumeResponse } from "@/types/resume";

interface JobDocumentsSectionProps {
  jobId: string;
}

export function JobDocumentsSection({ jobId }: JobDocumentsSectionProps) {
  const [resume, setResume] = useState<ResumeResponse | null>(null);
  const [coverLetter, setCoverLetter] = useState<CoverLetterListItem | null>(null);
  const [loading, setLoading] = useState(true);
  const [resumeGenerating, setResumeGenerating] = useState(false);
  const [coverGenerating, setCoverGenerating] = useState(false);
  const [jobResumeFile, setJobResumeFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const letters = await listCoverLetters(50, 0);
      const letterForJob = letters.cover_letters.find((cl) => cl.job_id === jobId) ?? null;
      setCoverLetter(letterForJob);

      try {
        const resumes = await listResumes(50, 0);
        const item = resumes.resumes.find((r) => r.job_id === jobId);
        if (item) {
          const detail = await getResume(item.id);
          if (detail.status === "completed") {
            setResume(detail);
          } else {
            setResume(null);
          }
        } else {
          setResume(null);
        }
      } catch {
        setResume(null);
      }
    } catch {
      setError("Failed to load documents for this job.");
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  async function handleGenerateResume(forceRegenerate = false) {
    setResumeGenerating(true);
    setError(null);
    try {
      if (jobResumeFile) {
        const formData = new FormData();
        formData.append("job_id", jobId);
        formData.append("force_regenerate", String(forceRegenerate));
        formData.append("resume_file", jobResumeFile);
        const response = await authenticatedFetch("/api/resumes/generate-with-upload", {
          method: "POST",
          body: formData,
        });
        if (!response.ok) {
          const body = await response.json().catch(() => ({}));
          throw new Error((body as { detail?: string }).detail ?? "Resume generation failed");
        }
      } else {
        await generateResume({ job_id: jobId, force_regenerate: forceRegenerate });
      }
      await loadDocuments();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to start resume generation";
      setError(message);
    } finally {
      setResumeGenerating(false);
    }
  }

  async function handleGenerateCoverLetter(forceRegenerate = false) {
    if (!resume) {
      setError("Generate a resume for this job before creating a cover letter.");
      return;
    }
    setCoverGenerating(true);
    setError(null);
    try {
      await generateCoverLetter({
        job_id: jobId,
        force_regenerate: forceRegenerate,
      });
      await loadDocuments();
    } catch (err: unknown) {
      const apiErr = err as { detail?: string };
      setError(apiErr.detail ?? "Failed to start cover letter generation");
    } finally {
      setCoverGenerating(false);
    }
  }

  if (loading) {
    return (
      <div className="rounded-lg border border-gray-200 bg-white p-4 animate-pulse h-32" />
    );
  }

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-4">
      <h3 className="text-sm font-semibold text-gray-900">Documents</h3>
      {error && <p className="text-sm text-red-600">{error}</p>}

      <div className="space-y-2">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Resume</p>
        {resume ? (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-700">
              ATS {resume.ats_score != null ? `${Math.round(resume.ats_score)}%` : "pending"}
            </span>
            <Link href={`/resumes/${resume.id}`} className="text-sm text-blue-600 hover:underline">
              View
            </Link>
            <ResumeDownloadButton resumeId={resume.id} />
            <button
              type="button"
              onClick={() => handleGenerateResume(true)}
              disabled={resumeGenerating}
              className="text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50"
            >
              Regenerate
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={(e) => setJobResumeFile(e.target.files?.[0] ?? null)}
              className="block w-full text-xs text-gray-500 file:mr-2 file:rounded file:border-0 file:bg-gray-100 file:px-2 file:py-1"
            />
            <button
              type="button"
              onClick={() => handleGenerateResume(false)}
              disabled={resumeGenerating}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {resumeGenerating ? "Starting..." : "Generate Resume"}
            </button>
          </div>
        )}
      </div>

      <div className="space-y-2 border-t border-gray-100 pt-3">
        <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">Cover Letter</p>
        {coverLetter ? (
          <div className="flex flex-wrap items-center gap-2">
            <Link
              href={`/cover-letters/${coverLetter.id}`}
              className="text-sm text-blue-600 hover:underline"
            >
              View
            </Link>
            <CoverLetterDownloadButton coverLetterId={coverLetter.id} />
            <button
              type="button"
              onClick={() => handleGenerateCoverLetter(true)}
              disabled={coverGenerating}
              className="text-sm text-gray-600 hover:text-gray-900 disabled:opacity-50"
            >
              Regenerate
            </button>
          </div>
        ) : (
          <div>
            <button
              type="button"
              onClick={() => handleGenerateCoverLetter(false)}
              disabled={coverGenerating || !resume}
              className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {coverGenerating ? "Starting..." : "Generate Cover Letter"}
            </button>
            {!resume && (
              <p className="mt-1 text-xs text-gray-500">
                Generate a resume first — the cover letter uses that content.
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
