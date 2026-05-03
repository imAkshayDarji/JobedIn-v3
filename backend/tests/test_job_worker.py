import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ApplicationStatus


USER_ID = str(uuid.uuid4())
APP_ID = str(uuid.uuid4())
JOB_ID = str(uuid.uuid4())


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


def _make_mock_session(query_results=None):
    session = AsyncMock()
    if query_results:
        results = []
        for val in query_results:
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = val
            results.append(mock_result)
        session.execute.side_effect = results
    return session


def _make_ingest_result(**overrides):
    result = MagicMock()
    result.new_count = overrides.get("new_count", 0)
    result.updated_count = overrides.get("updated_count", 0)
    result.skipped_count = overrides.get("skipped_count", 0)
    result.total_found = overrides.get("total_found", 0)
    result.errors = overrides.get("errors", [])
    result.model_dump.return_value = {
        "new_count": result.new_count,
        "updated_count": result.updated_count,
        "skipped_count": result.skipped_count,
        "total_found": result.total_found,
        "errors": result.errors,
    }
    return result


def _make_ats_detection_result(**overrides):
    result = MagicMock()
    result.ats_platform = overrides.get("ats_platform", "greenhouse")
    result.detection_method = overrides.get("detection_method", "html_analysis")
    result.confidence = overrides.get("confidence", 0.95)
    result.form_url = overrides.get("form_url", "https://boards.greenhouse.io/test")
    result.detected_fields = overrides.get("detected_fields", ["name", "email"])
    result.screenshot_path = overrides.get("screenshot_path", "/tmp/ats.png")
    result.error = overrides.get("error", None)
    result.detection_time_ms = overrides.get("detection_time_ms", 1500)
    difficulty = MagicMock()
    difficulty.value = overrides.get("difficulty_value", "medium")
    result.difficulty = difficulty
    return result


def _make_mock_application(status=ApplicationStatus.generating, user_id=USER_ID):
    app = MagicMock()
    app.id = uuid.UUID(APP_ID)
    app.user_id = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
    app.status = status
    app.ats_platform = None
    app.ats_detection_method = None
    app.ats_confidence = None
    app.ats_form_url = None
    app.ats_detected_fields = None
    app.ats_screenshot_path = None
    app.ats_detection_error = None
    app.ats_difficulty = None
    return app


class _BrowserCtxMgr:
    def __init__(self, browser):
        self._browser = browser

    async def __aenter__(self):
        return self._browser

    async def __aexit__(self, *args):
        pass


class _BrowserSvcMock:
    def __init__(self, browser):
        self._browser = browser

    def __call__(self, **kwargs):
        return _BrowserCtxMgr(self._browser)


@pytest.mark.asyncio
async def test_linkedin_discovery_job_success():
    ingest = _make_ingest_result(new_count=0, total_found=10)
    mock_service = MagicMock()
    mock_service.run_linkedin_discovery = AsyncMock(return_value=ingest)

    redis = AsyncMock()
    ctx = {"redis": redis}
    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import linkedin_discovery_job
        result = await linkedin_discovery_job(ctx, USER_ID, ["python"], "Remote")

    assert result["total_found"] == 10
    assert result["new_count"] == 0


@pytest.mark.asyncio
async def test_linkedin_discovery_job_with_new_jobs_enqueue_match():
    ingest = _make_ingest_result(new_count=5, total_found=10)
    mock_service = MagicMock()
    mock_service.run_linkedin_discovery = AsyncMock(return_value=ingest)

    mock_redis = AsyncMock()
    mock_redis.enqueue_job = AsyncMock()
    ctx = {"redis": mock_redis}
    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import linkedin_discovery_job
        result = await linkedin_discovery_job(ctx, USER_ID, ["python"], "Remote")

    assert result["new_count"] == 5


@pytest.mark.asyncio
async def test_linkedin_discovery_job_captcha_error():
    from app.services.job_sources.exceptions import LinkedInCAPTCHAError

    mock_service = MagicMock()
    mock_service.run_linkedin_discovery = AsyncMock(side_effect=LinkedInCAPTCHAError("CAPTCHA detected"))

    ctx = {"redis": AsyncMock()}
    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import linkedin_discovery_job
        result = await linkedin_discovery_job(ctx, USER_ID, ["python"], "Remote")

    assert len(result["errors"]) == 1
    assert "CAPTCHA" in result["errors"][0]


@pytest.mark.asyncio
async def test_linkedin_discovery_job_timeout_error():
    from app.services.job_sources.exceptions import LinkedInTimeoutError

    mock_service = MagicMock()
    mock_service.run_linkedin_discovery = AsyncMock(side_effect=LinkedInTimeoutError("Timeout"))

    ctx = {"redis": AsyncMock()}
    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import linkedin_discovery_job
        result = await linkedin_discovery_job(ctx, USER_ID, ["python"], "Remote")

    assert len(result["errors"]) == 1
    assert "Timeout" in result["errors"][0]


@pytest.mark.asyncio
async def test_linkedin_discovery_job_auth_error():
    from app.services.job_sources.exceptions import LinkedInAuthError

    mock_service = MagicMock()
    mock_service.run_linkedin_discovery = AsyncMock(side_effect=LinkedInAuthError("Auth failed"))

    ctx = {"redis": AsyncMock()}
    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import linkedin_discovery_job
        result = await linkedin_discovery_job(ctx, USER_ID, ["python"], "Remote")

    assert len(result["errors"]) == 1
    assert "Auth" in result["errors"][0]


@pytest.mark.asyncio
async def test_api_discovery_job_success():
    ingest = _make_ingest_result(new_count=3, total_found=8)
    mock_service = MagicMock()
    mock_service.run_api_discovery = AsyncMock(return_value=ingest)

    session = _make_mock_session()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import api_discovery_job
        result = await api_discovery_job({}, ["python"], "NYC", ["adzuna"])

    assert result["new_count"] == 3
    assert result["total_found"] == 8
    session.add.assert_called_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_match_jobs_job_success():
    score_result_1 = MagicMock()
    score_result_1.match_score = 0.85
    score_result_2 = MagicMock()
    score_result_2.match_score = 0.75

    mock_scorer = MagicMock()
    mock_scorer.score_jobs_batch = AsyncMock(return_value=[score_result_1, score_result_2])

    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.match_scorer.MatchScorer", return_value=mock_scorer):

        from app.workers.job_worker import match_jobs_job
        result = await match_jobs_job({}, USER_ID)

    assert result["scored_count"] == 2
    assert result["avg_score"] == 0.8


@pytest.mark.asyncio
async def test_ats_detect_job_success():
    application = _make_mock_application()
    session = _make_mock_session(query_results=[application])
    session_factory = _AsyncSessionMock(session)

    detection = _make_ats_detection_result()
    browser = AsyncMock()

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.browser_service.BrowserService", _BrowserSvcMock(browser)), \
         patch("app.services.ats_detector.ATSDetector") as MockATSDet:

        mock_detector = MagicMock()
        mock_detector.detect = AsyncMock(return_value=detection)
        MockATSDet.return_value = mock_detector

        from app.workers.job_worker import ats_detect_job
        result = await ats_detect_job({}, APP_ID, USER_ID, "https://example.com/apply")

    assert result["status"] == "completed"
    assert result["ats_platform"] == "greenhouse"
    assert application.ats_platform == "greenhouse"
    assert application.ats_confidence == 0.95
    assert application.status == ApplicationStatus.ready


@pytest.mark.asyncio
async def test_ats_detect_job_application_deleted():
    session = _make_mock_session(query_results=[None])
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.job_worker import ats_detect_job
        result = await ats_detect_job({}, APP_ID, USER_ID, "https://example.com/apply")

    assert result["status"] == "skipped"
    assert result["reason"] == "application_deleted"


@pytest.mark.asyncio
async def test_ats_detect_job_failure_reverts_status():
    application = _make_mock_application()
    session = _make_mock_session(query_results=[application])
    session_factory = _AsyncSessionMock(session)

    browser = AsyncMock()

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.browser_service.BrowserService", _BrowserSvcMock(browser)), \
         patch("app.services.ats_detector.ATSDetector") as MockATSDet:

        mock_detector = MagicMock()
        mock_detector.detect = AsyncMock(side_effect=Exception("Detection failed"))
        MockATSDet.return_value = mock_detector

        from app.workers.job_worker import ats_detect_job
        result = await ats_detect_job({}, APP_ID, USER_ID, "https://example.com/apply")

    assert result["status"] == "failed"
    assert application.status == ApplicationStatus.saved


@pytest.mark.asyncio
async def test_sweep_stale_ats_detections_reverts():
    session = AsyncMock()
    reverted_id = uuid.uuid4()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [reverted_id]
    session.execute.return_value = mock_result
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.job_worker import sweep_stale_ats_detections
        await sweep_stale_ats_detections({})

    session.execute.assert_awaited()
    session.commit.assert_awaited()
