import html
from pathlib import Path

from weasyprint import HTML

from app.schemas.ai import CoverLetterContent, ResumeContent

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_RESUME_CSS = (_TEMPLATE_DIR / "resume.css").read_text(encoding="utf-8")


class ResumePDFGenerator:
    def generate(
        self,
        resume_content: ResumeContent,
        job_title: str,
        company_name: str,
        user_name: str,
    ) -> bytes:
        sections_html: list[str] = []
        for section in sorted(resume_content.sections, key=lambda s: s.order):
            bullets = "".join(
                f"<li>{html.escape(point.text)}</li>"
                for point in section.bullet_points
            )
            bullet_block = f'<ul class="bullet-list">{bullets}</ul>' if bullets else ""
            prose = (
                f'<p class="prose">{html.escape(section.content)}</p>'
                if section.content
                else ""
            )
            sections_html.append(
                f'<div class="section">'
                f'<h2 class="section-title">{html.escape(section.title)}</h2>'
                f"{prose}{bullet_block}"
                f"</div>"
            )

        subtitle_parts = [p for p in [job_title, company_name] if p.strip()]
        subtitle = " — ".join(subtitle_parts) if subtitle_parts else ""

        document_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <style>{_RESUME_CSS}</style>
</head>
<body>
  <div class="header">
    <h1>{html.escape(user_name)}</h1>
    {f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ''}
  </div>
  {''.join(sections_html)}
</body>
</html>"""
        return HTML(string=document_html).write_pdf()


class CoverLetterPDFGenerator:
    def generate(
        self,
        cover_letter_content: CoverLetterContent,
        job_title: str,
        company_name: str,
        user_name: str,
    ) -> bytes:
        paragraphs_html: list[str] = []
        for paragraph in cover_letter_content.paragraphs:
            heading = (
                f"<h3>{html.escape(paragraph.heading)}</h3>"
                if paragraph.heading
                else ""
            )
            paragraphs_html.append(
                f"{heading}<p>{html.escape(paragraph.body)}</p>"
            )

        subtitle_parts = [p for p in [job_title, company_name] if p.strip()]
        subtitle = " — ".join(subtitle_parts) if subtitle_parts else ""

        document_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <style>{_RESUME_CSS}</style>
</head>
<body>
  <div class="header">
    <h1>{html.escape(user_name)}</h1>
    {f'<p class="subtitle">{html.escape(subtitle)}</p>' if subtitle else ''}
  </div>
  <div class="cover-letter-body">
    {''.join(paragraphs_html)}
  </div>
</body>
</html>"""
        return HTML(string=document_html).write_pdf()
