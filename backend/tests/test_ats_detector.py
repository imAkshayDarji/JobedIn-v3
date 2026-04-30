import pytest

from app.services.ats_detector import ATSDetector, ATSDifficulty, ATSDetectionResult


class TestATSDetectorURLPatterns:
    """Test Phase 1: URL pattern matching (no browser needed)."""

    def test_detect_greenhouse_boards_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://boards.greenhouse.io/company/jobs/123")
        assert result is not None
        assert result.ats_platform == "greenhouse"
        assert result.detection_method == "url_pattern"
        assert result.confidence == 1.0
        assert result.difficulty == ATSDifficulty.easy_apply

    def test_detect_greenhouse_job_boards_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://job-boards.greenhouse.io/company/jobs/456")
        assert result is not None
        assert result.ats_platform == "greenhouse"

    def test_detect_lever_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://jobs.lever.co/company/abc-123")
        assert result is not None
        assert result.ats_platform == "lever"
        assert result.detection_method == "url_pattern"
        assert result.confidence == 1.0
        assert result.difficulty == ATSDifficulty.easy_apply

    def test_detect_workday_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://mycompany.wd1.myworkdayjobs.com/en-US/jobs/123")
        assert result is not None
        assert result.ats_platform == "workday"
        assert result.detection_method == "url_pattern"
        assert result.confidence == 1.0
        assert result.difficulty == ATSDifficulty.multi_step

    def test_detect_workday_wd5_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://mycompany.wd5.myworkdayjobs.com/jobs/456")
        assert result is not None
        assert result.ats_platform == "workday"

    def test_detect_workday_bare_url(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://myworkdayjobs.com/company/jobs/789")
        assert result is not None
        assert result.ats_platform == "workday"

    def test_unknown_url_returns_none(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://careers.company.com/jobs/123")
        assert result is None


class TestATSDifficultyClassification:
    """Test difficulty classification per ATS platform."""

    def test_greenhouse_is_easy_apply(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://boards.greenhouse.io/test/jobs/1")
        assert result.difficulty == ATSDifficulty.easy_apply

    def test_lever_is_easy_apply(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://jobs.lever.co/test/abc")
        assert result.difficulty == ATSDifficulty.easy_apply

    def test_workday_is_multi_step(self):
        detector = ATSDetector.__new__(ATSDetector)
        result = detector.detect_from_url("https://test.wd1.myworkdayjobs.com/jobs/1")
        assert result.difficulty == ATSDifficulty.multi_step

    def test_unknown_is_manual_only(self):
        assert ATSDifficulty.manual_only == "manual_only"


class TestATSDetectionResult:
    """Test the ATSDetectionResult model."""

    def test_default_values(self):
        result = ATSDetectionResult(
            ats_platform=None,
            detection_method="failed",
            apply_url="https://example.com",
        )
        assert result.confidence == 0.0
        assert result.difficulty == ATSDifficulty.manual_only
        assert result.detected_fields == []
        assert result.error is None
        assert result.screenshot_path is None
        assert result.detection_time_ms == 0

    def test_full_result(self):
        result = ATSDetectionResult(
            ats_platform="greenhouse",
            detection_method="url_pattern",
            apply_url="https://boards.greenhouse.io/test/jobs/1",
            confidence=1.0,
            difficulty=ATSDifficulty.easy_apply,
            detected_fields=["name", "email"],
            detection_time_ms=150,
        )
        assert result.ats_platform == "greenhouse"
        assert result.confidence == 1.0
        assert len(result.detected_fields) == 2


class TestATSDetectorDetectFromURLSSRF:
    """Test that detect() validates URLs for SSRF before browsing."""

    @pytest.mark.asyncio
    async def test_detect_blocks_private_ip(self):
        from unittest.mock import AsyncMock

        from app.services.browser_service import BrowserService

        browser = AsyncMock(spec=BrowserService)
        detector = ATSDetector(browser)
        result = await detector.detect("https://192.168.1.1/jobs")
        assert result.detection_method == "failed"
        assert result.error is not None
        assert "private" in result.error.lower()

    @pytest.mark.asyncio
    async def test_detect_blocks_localhost(self):
        from unittest.mock import AsyncMock

        from app.services.browser_service import BrowserService

        browser = AsyncMock(spec=BrowserService)
        detector = ATSDetector(browser)
        result = await detector.detect("https://localhost/jobs")
        assert result.detection_method == "failed"
        assert result.error is not None
