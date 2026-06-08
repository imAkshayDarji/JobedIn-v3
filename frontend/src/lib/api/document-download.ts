import { authenticatedFetch } from "@/lib/api";

interface PdfUrlResponse {
  url: string;
}

async function openPdfUrl(path: string): Promise<void> {
  const response = await authenticatedFetch(path, {
    method: "GET",
  });

  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail =
      (body as { detail?: string }).detail ?? "Failed to download PDF";
    throw new Error(detail);
  }

  const data = (await response.json()) as PdfUrlResponse;
  if (!data.url) {
    throw new Error("Download URL missing from response");
  }
  window.open(data.url, "_blank", "noopener,noreferrer");
}

export async function downloadResumePdf(resumeId: string): Promise<void> {
  await openPdfUrl(`/api/resumes/${resumeId}/pdf`);
}

export async function downloadCoverLetterPdf(coverLetterId: string): Promise<void> {
  await openPdfUrl(`/api/cover-letters/${coverLetterId}/pdf`);
}
