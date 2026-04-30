import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.models.application import Application
from app.models.base import ApplicationStatus
from app.schemas.apply import ATSDetectRequest

TEST_JWT_SECRET = "test-jwt-secret-for-testing-only-min-32-chars!!"
TEST_SUPABASE_URL = "https://test.supabase.co"
TEST_USER_ID = str(uuid.uuid4())


def _mint_jwt(
    user_id: str = TEST_USER_ID,
    email: str = "test@example.com",
    secret: str = TEST_JWT_SECRET,
) -> str:
    import jwt as pyjwt

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "role": "authenticated",
        "iss": f"{TEST_SUPABASE_URL}/auth/v1",
        "iat": now,
        "exp": now + timedelta(hours=1),
        "aud": "authenticated",
    }
    return pyjwt.encode(payload, secret, algorithm="HS256")


@pytest.fixture(autouse=True)
def _set_test_settings():
    with patch.object(settings, "SUPABASE_JWT_SECRET", TEST_JWT_SECRET), patch.object(
        settings, "SUPABASE_URL", TEST_SUPABASE_URL
    ):
        yield


def _make_mock_session(return_values: list):
    """Create a mock async session where execute() returns pre-set scalars."""
    session = AsyncMock()
    results = []
    for val in return_values:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = val
        results.append(mock_result)

    session.execute.side_effect = results
    return session


class TestGetDetectionStatus:
    @pytest.mark.asyncio
    async def test_status_not_found(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_status

        mock_session = _make_mock_session([None])
        user = CurrentUser(id=uuid.UUID(TEST_USER_ID), email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_status(uuid.uuid4(), user, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_status_not_owned(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_status

        other_user_app = Application(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([other_user_app])
        user = CurrentUser(id=uuid.UUID(TEST_USER_ID), email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_status(other_user_app.id, user, mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_status_success(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_status

        user_id = uuid.UUID(TEST_USER_ID)
        app_id = uuid.uuid4()
        job_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=user_id,
            job_id=job_id,
            status=ApplicationStatus.ready,
            ats_platform="greenhouse",
            ats_detection_method="url_pattern",
            ats_confidence=1.0,
            ats_difficulty="easy_apply",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=user_id, email="test@example.com")
        response = await get_detection_status(app_id, user, mock_session)

        assert response.application_id == app_id
        assert response.ats_platform == "greenhouse"
        assert response.ats_difficulty == "easy_apply"


class TestScreenshot:
    @pytest.mark.asyncio
    async def test_screenshot_not_found(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_screenshot

        mock_session = _make_mock_session([None])
        user = CurrentUser(id=uuid.UUID(TEST_USER_ID), email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_screenshot(uuid.uuid4(), user, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_screenshot_path_traversal_blocked(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_screenshot

        user_id = uuid.UUID(TEST_USER_ID)
        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=user_id,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
            ats_screenshot_path="/etc/passwd",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=user_id, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_screenshot(app_id, user, mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_screenshot_no_path(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_screenshot

        user_id = uuid.UUID(TEST_USER_ID)
        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=user_id,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=user_id, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_screenshot(app_id, user, mock_session)
        assert exc_info.value.status_code == 404


class TestDetect:
    @pytest.mark.asyncio
    async def test_detect_no_apply_url(self):
        from app.auth import CurrentUser
        from app.models.job import Job
        from app.routes.apply import detect_ats

        user_id = uuid.UUID(TEST_USER_ID)
        job_id = uuid.uuid4()

        mock_job = Job(
            id=job_id,
            source="linkedin",
            title="Test",
            company="TestCo",
        )

        mock_session = _make_mock_session([mock_job])
        user = CurrentUser(id=user_id, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await detect_ats(request, user, mock_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_detect_job_not_found(self):
        from app.auth import CurrentUser
        from app.routes.apply import detect_ats

        user_id = uuid.UUID(TEST_USER_ID)
        job_id = uuid.uuid4()

        mock_session = _make_mock_session([None])
        user = CurrentUser(id=user_id, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await detect_ats(request, user, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_detect_no_application(self):
        from app.auth import CurrentUser
        from app.models.job import Job
        from app.routes.apply import detect_ats

        user_id = uuid.UUID(TEST_USER_ID)
        job_id = uuid.uuid4()

        mock_job = Job(
            id=job_id,
            source="linkedin",
            title="Test",
            company="TestCo",
            apply_url="https://boards.greenhouse.io/test/jobs/1",
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = mock_job
        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [job_result, app_result]

        user = CurrentUser(id=user_id, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await detect_ats(request, user, mock_session)
        assert exc_info.value.status_code == 404
