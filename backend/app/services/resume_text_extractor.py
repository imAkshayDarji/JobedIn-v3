import io

from fastapi import HTTPException, status


def extract_text_from_resume_bytes(content: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf_text(content)
    if lower.endswith(".docx"):
        return _extract_docx_text(content)
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail="Only PDF and DOCX files are accepted",
    )


def _extract_pdf_text(content: bytes) -> str:
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(io.BytesIO(content))
        text_parts: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
        return "\n".join(text_parts)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse PDF. Please ensure the file is a valid PDF document.",
        ) from exc


def _extract_docx_text(content: bytes) -> str:
    try:
        from docx import Document

        document = Document(io.BytesIO(content))
        paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Failed to parse DOCX. Please ensure the file is a valid Word document.",
        ) from exc
