import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ApplicationStatus


APP_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
BULK_TASK_ID = str(uuid.uuid4())


class _AsyncSessionMock:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return _AsyncCtxMgr(self._session)


class _AsyncCtxMgr:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _make_mock_session():
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock()
    session.execute.return_value = mock_result
    return session


def _make_orchestrator_result(**overrides):
    result = MagicMock()
    result.application_id = uuid.UUID(APP_ID)
    result.success = True
    result.status = "applied"
    result.resume_id = None
    result.cover_letter_id = None
    result.screenshot_path = "/tmp/screenshot.png"
    result.manual_url = None
    result.error = None
    result.steps_completed = ["navigate", "fill", "submit"]
    result.total_latency_ms = 5000
    for k, v in overrides.items():
        setattr(result, k, v)
    result.model_dump.return_value = {
        "application_id": APP_ID,
        "success": result.success,
        "status": result.status,
        "screenshot_path": result.screenshot_path,
        "steps_completed": result.steps_completed,
        "total_latency_ms": result.total_latency_ms,
    }
    return result


class _BrowserCtxMgr:
    def __init__(self, browser):
        self._browser = browser

    async def __aenter__(self):
        return self._browser

    async def __aexit__(self, *args):
        pass


class _BrowserSvcMock:
    """Mimics BrowserService constructor + context manager: BrowserService(...) returns an async ctx mgr."""

    def __init__(self, browser):
        self._browser = browser

    def __call__(self, **kwargs):
        return _BrowserCtxMgr(self._browser)


@pytest.mark.asyncio
async def test_apply_single_job_success():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock()
    ctx = {"redis": redis}

    mock_result = _make_orchestrator_result()
    mock_orchestrator = MagicMock()
    mock_orchestrator.run = AsyncMock(return_value=mock_result)

    mock_session = _make_mock_session()
    session_factory = _AsyncSessionMock(mock_session)
    browser = AsyncMock()

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.browser_service.BrowserService", _BrowserSvcMock(browser)), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=MagicMock()), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()), \
         patch("app.services.apply_orchestrator.AutoApplyOrchestrator", return_value=mock_orchestrator):

        from app.workers.apply_worker import apply_single_job
        result = await apply_single_job(ctx, APP_ID, USER_ID)

    assert result["status"] == "applied"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_apply_single_job_skipped_locked():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"locked")
    ctx = {"redis": redis}

    from app.workers.apply_worker import apply_single_job
    result = await apply_single_job(ctx, APP_ID, USER_ID)

    assert result["status"] == "skipped"
    assert result["reason"] == "lock_held"


@pytest.mark.asyncio
async def test_apply_single_job_failure():
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    ctx = {"redis": redis}

    mock_session = _make_mock_session()
    mock_update_result = MagicMock()
    mock_session.execute.side_effect = [mock_update_result]
    session_factory = _AsyncSessionMock(mock_session)

    class _FailBrowserSvc:
        def __call__(self, **kwargs):
            return _FailBrowserCtx()

    class _FailBrowserCtx:
        async def __aenter__(self):
            raise Exception("Browser crashed")
        async def __aexit__(self, *args):
            pass

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.browser_service.BrowserService", _FailBrowserSvc()), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=MagicMock()), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()), \
         patch("app.services.apply_orchestrator.AutoApplyOrchestrator"):

        from app.workers.apply_worker import apply_single_job
        result = await apply_single_job(ctx, APP_ID, USER_ID)

    assert result["status"] == "failed"
    assert "Browser crashed" in result["error"]


@pytest.mark.asyncio
async def test_apply_bulk_job_processes_all():
    redis = AsyncMock()
    ctx = {"redis": redis}

    app_ids = [str(uuid.uuid4()) for _ in range(3)]

    with patch("app.workers.apply_worker.apply_single_job", new_callable=AsyncMock) as mock_single:
        mock_single.return_value = {"status": "applied", "application_id": app_ids[0]}

        from app.workers.apply_worker import apply_bulk_job
        result = await apply_bulk_job(ctx, app_ids, USER_ID, BULK_TASK_ID)

    assert mock_single.call_count == 3
    assert result["total"] == 3
    assert result["bulk_task_id"] == BULK_TASK_ID


@pytest.mark.asyncio
async def test_apply_bulk_job_initializes_progress():
    redis = AsyncMock()
    ctx = {"redis": redis}

    app_ids = [str(uuid.uuid4()) for _ in range(2)]

    with patch("app.workers.apply_worker.apply_single_job", new_callable=AsyncMock) as mock_single:
        mock_single.return_value = {"status": "applied"}

        from app.workers.apply_worker import apply_bulk_job
        await apply_bulk_job(ctx, app_ids, USER_ID, BULK_TASK_ID)

    redis.set.assert_any_call(
        f"apply_bulk:{BULK_TASK_ID}",
        json.dumps({"total": 2, "completed": 0, "failed": 0, "manual_required": 0, "pending": 2, "results": []}),
        ex=86400,
    )


@pytest.mark.asyncio
async def test_sweep_stale_apply_jobs_reverts():
    redis = AsyncMock()
    ctx = {"redis": redis}

    reverted_id = uuid.uuid4()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [reverted_id]
    mock_session.execute.return_value = mock_result
    session_factory = _AsyncSessionMock(mock_session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.apply_worker import sweep_stale_apply_jobs
        await sweep_stale_apply_jobs(ctx)

    mock_session.execute.assert_awaited()
    mock_session.commit.assert_awaited()
    redis.delete.assert_any_call(f"apply_lock:{reverted_id}")
    redis.delete.assert_any_call(f"apply_progress:{reverted_id}")


@pytest.mark.asyncio
async def test_update_bulk_progress_increments_completed():
    redis = AsyncMock()
    existing_data = json.dumps({
        "total": 3,
        "completed": 1,
        "failed": 0,
        "manual_required": 0,
        "pending": 2,
        "results": [],
    })
    redis.get = AsyncMock(return_value=existing_data)

    from app.workers.apply_worker import _update_bulk_progress
    await _update_bulk_progress(redis, BULK_TASK_ID, {"status": "applied", "application_id": APP_ID})

    set_call = redis.set.call_args
    updated = json.loads(set_call[0][1])
    assert updated["completed"] == 2
    assert updated["pending"] == 1
    assert len(updated["results"]) == 1
