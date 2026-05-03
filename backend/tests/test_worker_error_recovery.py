import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ApplicationStatus


USER_ID = str(uuid.uuid4())
OTHER_USER_ID = str(uuid.uuid4())
APP_ID = str(uuid.uuid4())


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
async def test_ats_detect_job_user_mismatch():
    """ats_detect_job skips when application.user_id does not match the requesting user."""
    application = _make_mock_application(user_id=OTHER_USER_ID)
    session = _make_mock_session(query_results=[application])
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.job_worker import ats_detect_job
        result = await ats_detect_job({}, APP_ID, USER_ID, "https://example.com/apply")

    assert result["status"] == "skipped"
    assert result["reason"] == "user_mismatch"


@pytest.mark.asyncio
async def test_api_discovery_job_service_exception():
    """api_discovery_job catches generic exceptions and returns error result."""
    mock_service = MagicMock()
    mock_service.run_api_discovery = AsyncMock(side_effect=Exception("External API down"))

    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import api_discovery_job
        result = await api_discovery_job({}, ["python"], "NYC", ["adzuna"])

    assert "error" in str(result.get("errors", [])).lower() or "External API down" in str(result.get("errors", []))


@pytest.mark.asyncio
async def test_match_jobs_job_empty_results():
    """match_jobs_job returns scored_count=0 and avg_score=0.0 when scorer returns empty list."""
    mock_scorer = MagicMock()
    mock_scorer.score_jobs_batch = AsyncMock(return_value=[])

    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.match_scorer.MatchScorer", return_value=mock_scorer):

        from app.workers.job_worker import match_jobs_job
        result = await match_jobs_job({}, USER_ID)

    assert result["scored_count"] == 0
    assert result["avg_score"] == 0.0


@pytest.mark.asyncio
async def test_generate_resume_job_resume_deleted_between_sessions():
    """generate_resume_job completes even if resume is deleted between the first and second DB query."""
    resume = MagicMock()
    resume.id = APP_ID
    resume.status = "pending"
    resume.content_json = None
    resume.ats_score = None
    resume.ats_breakdown = None

    session = _make_mock_session(query_results=[resume, None])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_full_pipeline = AsyncMock(return_value={
        "resume": {"sections": [{"type": "summary", "content": "Dev"}]},
        "ats_result": {"overall_score": 90, "breakdown": {}},
        "token_usage": {"calls": 0},
    })

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_resume_job
        result = await generate_resume_job(
            ctx={},
            resume_id=APP_ID,
            user_id=USER_ID,
            candidate_profile_id=str(uuid.uuid4()),
            job_description="Python Developer",
        )

    assert result.get("ats_result", {}).get("overall_score") == 90


@pytest.mark.asyncio
async def test_sweep_stale_ats_detections_no_stale():
    """sweep_stale_ats_detections commits session even when no stale records found."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.job_worker import sweep_stale_ats_detections
        await sweep_stale_ats_detections({})

    session.execute.assert_awaited()
    session.commit.assert_awaited()
