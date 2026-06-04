import logging

from app.models.cover_letter import CoverLetter
from app.models.resume import Resume
from app.services.resume_text_extractor import extract_text_from_resume_bytes
from app.services.s3_storage import S3Storage, S3StorageError

logger = logging.getLogger(__name__)


async def delete_resume_s3_assets(resume: Resume) -> None:
    keys = [resume.pdf_s3_key, resume.uploaded_resume_s3_key]
    try:
        storage = S3Storage()
    except S3StorageError:
        logger.warning(
            "s3_not_configured_skip_resume_delete",
            extra={"resume_id": str(resume.id)},
        )
        return
    for key in keys:
        if key:
            await storage.delete_file(key)


async def delete_cover_letter_s3_assets(cover_letter: CoverLetter) -> None:
    if not cover_letter.pdf_s3_key:
        return
    try:
        storage = S3Storage()
        await storage.delete_file(cover_letter.pdf_s3_key)
    except S3StorageError:
        logger.warning(
            "s3_not_configured_skip_cover_letter_delete",
            extra={"cover_letter_id": str(cover_letter.id)},
        )


async def load_resume_text_from_s3_key(s3_key: str) -> str:
    storage = S3Storage()
    content = await storage.download_file(s3_key)
    filename = s3_key.rsplit("/", 1)[-1]
    return extract_text_from_resume_bytes(content, filename)
