from app.schemas.ai import CoverLetterContent, CoverLetterParagraph, ResumeBulletPoint, ResumeContent, ResumeSection
from app.services.pdf_generator import CoverLetterPDFGenerator, ResumePDFGenerator


def test_resume_pdf_generator_produces_pdf_bytes() -> None:
    content = ResumeContent(
        sections=[
            ResumeSection(
                title="Experience",
                order=1,
                bullet_points=[
                    ResumeBulletPoint(text="Built scalable APIs", keywords_included=["API"]),
                ],
                content=None,
            ),
        ],
        target_keywords_covered=["API"],
        overall_keyword_coverage=80.0,
    )
    pdf_bytes = ResumePDFGenerator().generate(
        resume_content=content,
        job_title="Software Engineer",
        company_name="Acme Corp",
        user_name="Jane Doe",
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_cover_letter_pdf_generator_produces_pdf_bytes() -> None:
    content = CoverLetterContent(
        paragraphs=[
            CoverLetterParagraph(heading=None, body="Dear Hiring Manager,"),
            CoverLetterParagraph(heading=None, body="I am excited to apply."),
        ],
        tone_used="professional",
        keywords_addressed=["leadership"],
        full_text="Dear Hiring Manager,\n\nI am excited to apply.",
    )
    pdf_bytes = CoverLetterPDFGenerator().generate(
        cover_letter_content=content,
        job_title="Software Engineer",
        company_name="Acme Corp",
        user_name="Jane Doe",
    )
    assert pdf_bytes.startswith(b"%PDF")
