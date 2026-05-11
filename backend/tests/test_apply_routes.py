import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.config import settings
from app.models.application import Application
from app.models.base import ApplicationStatus
from app.schemas.apply import ATSDetectRequest
from tests.conftest import _mock_decode_token

TEST_USER_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _set_test_settings():
    with patch.object(settings, "CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json"), \
         patch("app.auth._fetch_jwks", new_callable=AsyncMock, return_value={"test-kid": {}}), \
         patch("app.auth._decode_token", side_effect=_mock_decode_token):
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
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

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
            user_id=str(uuid.uuid4()),
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([other_user_app])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_status(other_user_app.id, user, mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_status_success(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_status

        app_id = uuid.uuid4()
        job_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=job_id,
            status=ApplicationStatus.ready,
            ats_platform="greenhouse",
            ats_detection_method="url_pattern",
            ats_confidence=1.0,
            ats_difficulty="easy_apply",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
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
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_screenshot(uuid.uuid4(), user, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_screenshot_path_traversal_blocked(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_screenshot

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
            ats_screenshot_path="/etc/passwd",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_detection_screenshot(app_id, user, mock_session)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_screenshot_no_path(self):
        from app.auth import CurrentUser
        from app.routes.apply import get_detection_screenshot

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

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

        job_id = uuid.uuid4()

        mock_job = Job(
            id=job_id,
            source="linkedin",
            title="Test",
            company="TestCo",
        )

        mock_session = _make_mock_session([mock_job])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await detect_ats(request, user, mock_session)
        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_detect_job_not_found(self):
        from app.auth import CurrentUser
        from app.routes.apply import detect_ats

        job_id = uuid.uuid4()

        mock_session = _make_mock_session([None])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
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

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await detect_ats(request, user, mock_session)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_detect_source_url_without_apply_url_enqueues(self):
        from app.auth import CurrentUser
        from app.models.application import Application
        from app.models.job import Job
        from app.routes.apply import detect_ats

        job_id = uuid.uuid4()
        app_id = uuid.uuid4()

        mock_job = Job(
            id=job_id,
            source="linkedin",
            title="Test",
            company="TestCo",
            source_url="https://careers.example.com/jobs/1",
            apply_url=None,
        )
        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=job_id,
            status=ApplicationStatus.saved,
        )

        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = mock_job
        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [job_result, app_result]
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ATSDetectRequest(job_id=job_id)

        mock_arq_job = MagicMock()
        mock_arq_job.job_id = "ats_task_789"
        mock_pool = AsyncMock()
        mock_pool.enqueue_job = AsyncMock(return_value=mock_arq_job)
        mock_pool.close = AsyncMock()

        with patch("app.routes.apply.arq_create_pool", return_value=mock_pool):
            response = await detect_ats(request, user, mock_session)

        assert response.application_id == app_id
        assert response.task_id == "ats_task_789"
        mock_pool.enqueue_job.assert_awaited_once()
        enqueue_call = mock_pool.enqueue_job.await_args
        assert enqueue_call.args[3] == ""
