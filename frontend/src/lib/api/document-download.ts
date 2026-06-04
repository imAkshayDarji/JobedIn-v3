import { authenticatedFetch } from "@/lib/api";

async function openPdfFromRedirect(path: string): Promise<void> {
  const response = await authenticatedFetch(path, {
    method: "GET",
    redirect: "manual",
  });

  if (response.status === 307 || response.status === 302) {
    const url = response.headers.get("Location");
    if (!url) {
      throw new Error("Download URL missing from response");
    }
    window.open(url, "_blank", "noopener,noreferrer");
    return;
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      (body as { detail?: string }).detail ?? "Failed to download PDF";
    throw new Error(detail);
  }

  throw new Error("Unexpected response when downloading PDF");
}

export async function downloadResumePdf(resumeId: string): Promise<void> {
  await openPdfFromRedirect(`/api/resumes/${resumeId}/pdf`);
}

export async function downloadCoverLetterPdf(coverLetterId: string): Promise<void> {
  await openPdfFromRedirect(`/api/cover-letters/${coverLetterId}/pdf`);
}
