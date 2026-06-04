import logging
from typing import Any

from aiobotocore.session import get_session
from botocore.exceptions import ClientError

from app.config import settings

logger = logging.getLogger(__name__)


class S3StorageError(Exception):
    def __init__(self, message: str, *, key: str | None = None) -> None:
        self.key = key
        super().__init__(message)


class S3Storage:
    def __init__(self) -> None:
        if not settings.S3_BUCKET_NAME.strip():
            raise S3StorageError(
                "S3_BUCKET_NAME is not configured; set AWS credentials and bucket in environment"
            )
        self._bucket = settings.S3_BUCKET_NAME.strip()
        self._region = settings.AWS_REGION.strip() or "us-east-1"

    def _session_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"region_name": self._region}
        if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
            kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
            kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
        return kwargs

    async def upload_file(self, file_bytes: bytes, key: str, content_type: str) -> str:
        if not key.strip():
            raise S3StorageError("S3 object key must not be empty", key=key)
        session = get_session()
        try:
            async with session.create_client("s3", **self._session_kwargs()) as client:
                await client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=file_bytes,
                    ContentType=content_type,
                )
        except ClientError as exc:
            raise S3StorageError(
                f"S3 upload failed for key={key}: {exc.response.get('Error', {}).get('Message', str(exc))}",
                key=key,
            ) from exc

        url = f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"
        logger.info("s3_upload_complete", extra={"key": key, "bytes": len(file_bytes)})
        return url

    async def download_file(self, key: str) -> bytes:
        if not key.strip():
            raise S3StorageError("S3 object key must not be empty", key=key)
        session = get_session()
        try:
            async with session.create_client("s3", **self._session_kwargs()) as client:
                response = await client.get_object(Bucket=self._bucket, Key=key)
                body = await response["Body"].read()
                return body
        except ClientError as exc:
            code = exc.response.get("Error", {}).get("Code", "")
            if code in ("NoSuchKey", "404"):
                raise S3StorageError(f"S3 object not found: key={key}", key=key) from exc
            raise S3StorageError(
                f"S3 download failed for key={key}: {exc.response.get('Error', {}).get('Message', str(exc))}",
                key=key,
            ) from exc

    async def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        if not key.strip():
            raise S3StorageError("S3 object key must not be empty", key=key)
        session = get_session()
        try:
            async with session.create_client("s3", **self._session_kwargs()) as client:
                url = await client.generate_presigned_url(
                    "get_object",
                    Params={"Bucket": self._bucket, "Key": key},
                    ExpiresIn=expires_in,
                )
                return url
        except ClientError as exc:
            raise S3StorageError(
                f"S3 presign failed for key={key}: {exc.response.get('Error', {}).get('Message', str(exc))}",
                key=key,
            ) from exc

    async def delete_file(self, key: str) -> None:
        if not key.strip():
            return
        session = get_session()
        try:
            async with session.create_client("s3", **self._session_kwargs()) as client:
                await client.delete_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            raise S3StorageError(
                f"S3 delete failed for key={key}: {exc.response.get('Error', {}).get('Message', str(exc))}",
                key=key,
            ) from exc
        logger.info("s3_delete_complete", extra={"key": key})


def upload_resume_key(user_id: str, filename: str) -> str:
    safe_name = filename.replace("/", "_").replace("\\", "_")
    return f"{settings.S3_RESUME_UPLOAD_PREFIX}/{user_id}/{safe_name}"


def generated_resume_pdf_key(user_id: str, resume_id: str) -> str:
    return f"{settings.S3_RESUME_GENERATED_PREFIX}/{user_id}/{resume_id}.pdf"


def generated_cover_letter_pdf_key(user_id: str, cover_letter_id: str) -> str:
    return f"{settings.S3_COVER_LETTER_PREFIX}/{user_id}/{cover_letter_id}.pdf"
