import pytest
from unittest.mock import AsyncMock

from app.services.ats_fillers.registry import ATSFillerRegistry


def _make_mock_browser_service() -> AsyncMock:
    service = AsyncMock()
    service.capture_screenshot.return_value = "/screenshots/test.png"
    return service


class TestATSFillerRegistry:
    def test_get_greenhouse_filler(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        filler = registry.get_filler("greenhouse")
        assert filler is not None

    def test_get_lever_filler(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        filler = registry.get_filler("lever")
        assert filler is not None

    def test_get_workday_filler(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        filler = registry.get_filler("workday")
        assert filler is not None

    def test_get_unknown_returns_none(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        filler = registry.get_filler("unknown_platform")
        assert filler is None

    def test_supported_platforms(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        platforms = registry.supported_platforms()
        assert "greenhouse" in platforms
        assert "lever" in platforms
        assert "workday" in platforms
        assert len(platforms) == 3

    def test_returns_correct_filler_types(self):
        from app.services.ats_fillers.greenhouse import GreenhouseFiller
        from app.services.ats_fillers.lever import LeverFiller
        from app.services.ats_fillers.workday import WorkdayFiller

        registry = ATSFillerRegistry(_make_mock_browser_service())

        assert isinstance(registry.get_filler("greenhouse"), GreenhouseFiller)
        assert isinstance(registry.get_filler("lever"), LeverFiller)
        assert isinstance(registry.get_filler("workday"), WorkdayFiller)

    def test_supported_platforms_returns_list(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        platforms = registry.supported_platforms()
        assert isinstance(platforms, list)

    def test_case_sensitive_lookup(self):
        registry = ATSFillerRegistry(_make_mock_browser_service())
        assert registry.get_filler("Greenhouse") is None
        assert registry.get_filler("GREENHOUSE") is None
        assert registry.get_filler("greenhouse") is not None
