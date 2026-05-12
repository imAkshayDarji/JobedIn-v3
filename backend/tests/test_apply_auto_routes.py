import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.requests import Request as StarletteRequest

from app.config import settings
from app.models.application import Application
from app.models.base import ApplicationStatus, JobSource
from app.models.job import Job
from app.schemas.apply import ApplySinglePhase, ApplySingleRequest, ApplyBulkRequest
from tests.conftest import _mock_decode_token


def _make_mock_request():
    scope = {"type": "http", "method": "POST", "path": "/api/apply/single", "query_string": b"", "headers": []}
    return StarletteRequest(scope)

TEST_USER_ID = str(uuid.uuid4())
OTHER_USER_ID = str(uuid.uuid4())


@pytest.fixture(autouse=True)
def _disable_rate_limiting():
    from app.middleware.rate_limit import limiter
    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def _set_test_settings():
    with patch.object(settings, "CLERK_JWKS_URL", "https://clerk.test/.well-known/jwks.json"), \
         patch("app.auth._fetch_jwks", new_callable=AsyncMock, return_value={"test-kid": {}}), \
         patch("app.auth._decode_token", side_effect=_mock_decode_token):
        yield


def _make_mock_session(return_values: list):
    session = AsyncMock()
    results = []
    for val in return_values:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = val
        results.append(mock_result)

    session.execute.side_effect = results
    return session


class TestApplySingleSuccess:
    @pytest.mark.asyncio
    async def test_apply_single_success(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
            ats_platform="greenhouse",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        mock_arq_pool = AsyncMock()
        mock_arq_job = MagicMock()
        mock_arq_job.job_id = "test_task_123"
        mock_arq_pool.enqueue_job = AsyncMock(return_value=mock_arq_job)
        mock_arq_pool.close = AsyncMock()

        with patch("app.routes.apply.arq_create_pool", return_value=mock_arq_pool), \
             patch("app.routes.apply._clear_apply_progress", new_callable=AsyncMock):
            response = await apply_single(_make_mock_request(), request, user, mock_session)

        assert response.application_id == app_id
        assert response.task_id == "test_task_123"
        assert response.phase == ApplySinglePhase.applying
        assert application.status == ApplicationStatus.applying


class TestApplySingleGeneratingReturnsDetecting:
    @pytest.mark.asyncio
    async def test_apply_single_generating_is_idempotent(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.generating,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        response = await apply_single(_make_mock_request(), request, user, mock_session)

        assert response.phase == ApplySinglePhase.detecting
        assert application.status == ApplicationStatus.generating


class TestApplySingleSavedEnqueuesDetection:
    @pytest.mark.asyncio
    async def test_apply_single_saved_returns_detecting_phase(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()
        job_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=job_id,
            status=ApplicationStatus.saved,
        )
        job = Job(
            id=job_id,
            source=JobSource.linkedin,
            title="Engineer",
            company="Co",
            apply_url="https://boards.greenhouse.io/example/jobs/1",
        )

        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[app_result, job_result])
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        mock_arq_pool = AsyncMock()
        mock_arq_job = MagicMock()
        mock_arq_job.job_id = "ats_task_xyz"
        mock_arq_pool.enqueue_job = AsyncMock(return_value=mock_arq_job)
        mock_arq_pool.close = AsyncMock()

        with patch("app.routes.apply.arq_create_pool", return_value=mock_arq_pool), \
             patch("app.routes.apply._clear_apply_progress", new_callable=AsyncMock):
            response = await apply_single(_make_mock_request(), request, user, mock_session)

        assert response.phase == ApplySinglePhase.detecting
        assert response.task_id == "ats_task_xyz"
        assert application.status == ApplicationStatus.generating


class TestApplySingleApplyingIdempotent:
    @pytest.mark.asyncio
    async def test_apply_single_applying_returns_applying_phase(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.applying,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        response = await apply_single(_make_mock_request(), request, user, mock_session)

        assert response.phase == ApplySinglePhase.applying
        assert application.status == ApplicationStatus.applying


class TestApplySingleNotOwned:
    @pytest.mark.asyncio
    async def test_apply_single_not_owned(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=OTHER_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await apply_single(_make_mock_request(), request, user, mock_session)
        assert exc_info.value.status_code == 403


class TestApplySingleNotFound:
    @pytest.mark.asyncio
    async def test_apply_single_not_found(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        mock_session = _make_mock_session([None])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await apply_single(_make_mock_request(), request, user, mock_session)
        assert exc_info.value.status_code == 404


class TestApplySingleEnqueueFails:
    @pytest.mark.asyncio
    async def test_apply_single_enqueue_fails(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.ready,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplySingleRequest(application_id=app_id)

        with patch("app.routes.apply.arq_create_pool", side_effect=Exception("ARQ down")), \
             patch("app.routes.apply._clear_apply_progress", new_callable=AsyncMock):
            from fastapi import HTTPException

            with pytest.raises(HTTPException) as exc_info:
                await apply_single(_make_mock_request(), request, user, mock_session)
            assert exc_info.value.status_code == 502

        assert application.status == ApplicationStatus.ready


class TestApplyBulkSuccess:
    @pytest.mark.asyncio
    async def test_apply_bulk_success(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_bulk

        app_ids = [uuid.uuid4(), uuid.uuid4()]

        applications = [
            Application(id=aid, user_id=TEST_USER_ID, job_id=uuid.uuid4(), status=ApplicationStatus.ready)
            for aid in app_ids
        ]

        mock_session = _make_mock_session(applications)
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplyBulkRequest(application_ids=app_ids)

        mock_arq_pool = AsyncMock()
        mock_arq_pool.enqueue_job = AsyncMock()
        mock_arq_pool.close = AsyncMock()

        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock()
        mock_redis.aclose = AsyncMock()

        with patch("app.routes.apply.arq_create_pool", return_value=mock_arq_pool), \
             patch("app.routes.apply._get_raw_redis", return_value=mock_redis):
            response = await apply_bulk(_make_mock_request(), request, user, mock_session)

        assert response.bulk_task_id.startswith("apply_bulk_")
        assert len(response.application_ids) == 2
        assert all(a.status == ApplicationStatus.applying for a in applications)


class TestApplyBulkExceedsMax:
    @pytest.mark.asyncio
    async def test_apply_bulk_exceeds_max(self):
        from pydantic import ValidationError

        app_ids = [uuid.uuid4() for _ in range(11)]

        with pytest.raises(ValidationError) as exc_info:
            ApplyBulkRequest(application_ids=app_ids)
        assert "at most 10" in str(exc_info.value).lower() or "too_long" in str(exc_info.value)


class TestApplyBulkMixedStatus:
    @pytest.mark.asyncio
    async def test_apply_bulk_mixed_status(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_bulk

        app_id1 = uuid.uuid4()
        app_id2 = uuid.uuid4()

        app1 = Application(id=app_id1, user_id=TEST_USER_ID, job_id=uuid.uuid4(), status=ApplicationStatus.ready)
        app2 = Application(id=app_id2, user_id=TEST_USER_ID, job_id=uuid.uuid4(), status=ApplicationStatus.saved)

        result1 = MagicMock()
        result1.scalar_one_or_none.return_value = app1
        result2 = MagicMock()
        result2.scalar_one_or_none.return_value = app2

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [result1, result2]
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        request = ApplyBulkRequest(application_ids=[app_id1, app_id2])

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await apply_bulk(_make_mock_request(), request, user, mock_session)
        assert exc_info.value.status_code == 400


class TestApplyStatusSuccess:
    @pytest.mark.asyncio
    async def test_apply_status_success(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_status

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=TEST_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.applying,
            ats_platform="greenhouse",
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.aclose = AsyncMock()

        with patch("app.routes.apply._get_raw_redis", return_value=mock_redis):
            response = await apply_status(app_id, user, mock_session)

        assert response.application_id == app_id
        assert response.status == ApplicationStatus.applying.value


class TestApplyStatusNotOwned:
    @pytest.mark.asyncio
    async def test_apply_status_not_owned(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_status

        app_id = uuid.uuid4()

        application = Application(
            id=app_id,
            user_id=OTHER_USER_ID,
            job_id=uuid.uuid4(),
            status=ApplicationStatus.applying,
        )

        mock_session = _make_mock_session([application])
        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await apply_status(app_id, user, mock_session)
        assert exc_info.value.status_code == 403


class TestApplyBulkStatus:
    @pytest.mark.asyncio
    async def test_apply_bulk_status(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_bulk_status

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        bulk_data = json.dumps({
            "total": 3,
            "completed": 1,
            "failed": 1,
            "manual_required": 0,
            "pending": 1,
            "results": [
                {"application_id": str(uuid.uuid4()), "status": "applied"},
                {"application_id": str(uuid.uuid4()), "status": "failed", "error": "AI down"},
            ],
        })

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=bulk_data)
        mock_redis.aclose = AsyncMock()

        with patch("app.routes.apply._get_raw_redis", return_value=mock_redis):
            response = await apply_bulk_status("apply_bulk_test123", user)

        assert response.total == 3
        assert response.completed == 1
        assert response.failed == 1
        assert response.pending == 1


class TestApplyBulkStatusInitial:
    @pytest.mark.asyncio
    async def test_apply_bulk_status_initial(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_bulk_status

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")

        bulk_data = json.dumps({
            "total": 5,
            "completed": 0,
            "failed": 0,
            "manual_required": 0,
            "pending": 5,
            "results": [],
        })

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=bulk_data)
        mock_redis.aclose = AsyncMock()

        with patch("app.routes.apply._get_raw_redis", return_value=mock_redis):
            response = await apply_bulk_status("apply_bulk_initial", user)

        assert response.total == 5
        assert response.pending == 5
        assert response.completed == 0
        assert response.results == []
