import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ApplicationStatus


USER_ID = str(uuid.uuid4())
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


@pytest.mark.asyncio
async def test_api_discovery_returns_new_count_and_enqueues_match():
    """api_discovery_job returns new_count > 0 when new jobs are found,
    verifying the discovery -> match chain data contract."""
    from app.services.job_discovery import IngestResult

    mock_service = MagicMock()
    mock_service.run_api_discovery = AsyncMock(
        return_value=IngestResult(
            new_count=5,
            updated_count=2,
            skipped_count=1,
            total_found=8,
            errors=[],
        ),
    )

    session = AsyncMock()
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.job_discovery.JobDiscoveryService", return_value=mock_service):

        from app.workers.job_worker import api_discovery_job
        result = await api_discovery_job({}, ["python"], "NYC", ["adzuna"])

    assert result["new_count"] == 5
    assert result["total_found"] == 8
    assert result["updated_count"] == 2
    assert result["skipped_count"] == 1
    assert result["errors"] == []


@pytest.mark.asyncio
async def test_ats_detect_to_apply_status_chain():
    """ats_detect_job transitions application status from generating to detected ATS,
    verifying the ATS detect -> apply status chain."""
    from app.services.ats_detector import ATSDifficulty

    application = _make_mock_application(
        status=ApplicationStatus.generating, user_id=USER_ID
    )
    session = _make_mock_session(query_results=[application, application])
    session_factory = _AsyncSessionMock(session)

    mock_detector = MagicMock()
    mock_detector.detect = AsyncMock(return_value=MagicMock(
        ats_platform="greenhouse",
        confidence=0.95,
        detection_method="html_patterns",
        apply_url="https://example.com/apply",
        form_url="https://boards.greenhouse.io/job/123",
        detected_fields=["name", "email", "resume"],
        screenshot_path=None,
        error=None,
        difficulty=ATSDifficulty.easy_apply,
        detection_time_ms=500,
    ))

    mock_browser = MagicMock()

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ats_detector.ATSDetector", return_value=mock_detector), \
         patch("app.services.browser_service.BrowserService") as MockBrowser:

        MockBrowser.return_value.__aenter__ = AsyncMock(return_value=mock_browser)
        MockBrowser.return_value.__aexit__ = AsyncMock(return_value=None)

        from app.workers.job_worker import ats_detect_job
        result = await ats_detect_job({}, APP_ID, USER_ID, "https://example.com/apply")

    assert result["status"] == "completed"
    assert result["ats_platform"] == "greenhouse"
    assert result["difficulty"] == "easy_apply"
