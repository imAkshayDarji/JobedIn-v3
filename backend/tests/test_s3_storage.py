import pytest
from botocore.exceptions import ClientError

from app.config import settings
from app.services.s3_storage import S3Storage, upload_resume_key


@pytest.fixture
def s3_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "S3_BUCKET_NAME", "jobedin-test-bucket")
    monkeypatch.setattr(settings, "AWS_REGION", "us-east-1")
    monkeypatch.setattr(settings, "AWS_ACCESS_KEY_ID", "testing")
    monkeypatch.setattr(settings, "AWS_SECRET_ACCESS_KEY", "testing")


class _FakeS3Body:
    def __init__(self, data: bytes) -> None:
        self._data = data

    async def read(self) -> bytes:
        return self._data


class _FakeS3Client:
    def __init__(self) -> None:
        self._objects: dict[tuple[str, str], bytes] = {}

    async def __aenter__(self) -> "_FakeS3Client":
        return self

    async def __aexit__(self, *args: object) -> None:
        return None

    async def put_object(
        self,
        *,
        Bucket: str,
        Key: str,
        Body: bytes,
        ContentType: str,
    ) -> None:
        self._objects[(Bucket, Key)] = Body

    async def get_object(self, *, Bucket: str, Key: str) -> dict[str, _FakeS3Body]:
        payload = self._objects.get((Bucket, Key))
        if payload is None:
            raise ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "Not found"}},
                "GetObject",
            )
        return {"Body": _FakeS3Body(payload)}

    async def generate_presigned_url(
        self,
        operation: str,
        *,
        Params: dict[str, str],
        ExpiresIn: int,
    ) -> str:
        return (
            f"https://{Params['Bucket']}.s3.amazonaws.com/{Params['Key']}"
            f"?expires={ExpiresIn}"
        )

    async def delete_object(self, *, Bucket: str, Key: str) -> None:
        self._objects.pop((Bucket, Key), None)


class _FakeSession:
    def __init__(self) -> None:
        self._client = _FakeS3Client()

    def create_client(self, *_args: object, **_kwargs: object) -> _FakeS3Client:
        return self._client


@pytest.mark.asyncio
async def test_s3_upload_download_delete(s3_env: None, monkeypatch: pytest.MonkeyPatch) -> None:
    fake_session = _FakeSession()
    monkeypatch.setattr(
        "app.services.s3_storage.get_session",
        lambda: fake_session,
    )
    storage = S3Storage()
    key = upload_resume_key("user-1", "resume.pdf")
    payload = b"%PDF-1.4 test content"

    await storage.upload_file(payload, key, "application/pdf")
    downloaded = await storage.download_file(key)
    assert downloaded == payload

    url = await storage.get_presigned_url(key, expires_in=300)
    assert "jobedin-test-bucket" in url
    assert key in url

    await storage.delete_file(key)
    with pytest.raises(Exception):
        await storage.download_file(key)


def test_upload_resume_key_sanitizes_path_segments(s3_env: None) -> None:
    key = upload_resume_key("user-1", "my/resume.pdf")
    assert key.endswith("my_resume.pdf")
    assert key.startswith(f"{settings.S3_RESUME_UPLOAD_PREFIX}/user-1/")
