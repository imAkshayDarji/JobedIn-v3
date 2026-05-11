import logging
import re
import time
from enum import StrEnum
from typing import TYPE_CHECKING

from pydantic import BaseModel

from app.services.url_validator import validate_apply_url

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)


class ATSDifficulty(StrEnum):
    easy_apply = "easy_apply"
    multi_step = "multi_step"
    manual_only = "manual_only"
    manual_assist = "manual_assist"


class ATSDetectionResult(BaseModel):
    ats_platform: str | None
    detection_method: str  # "url_pattern" | "dom_inspection" | "failed"
    apply_url: str
    form_url: str | None = None
    screenshot_path: str | None = None
    detected_fields: list[str] = []
    difficulty: ATSDifficulty = ATSDifficulty.manual_only
    confidence: float = 0.0
    error: str | None = None
    detection_time_ms: int = 0


ATS_URL_PATTERNS: dict[str, list[re.Pattern[str]]] = {
    "greenhouse": [
        re.compile(r"boards\.greenhouse\.io/"),
        re.compile(r"job-boards\.greenhouse\.io/"),
    ],
    "lever": [
        re.compile(r"jobs\.lever\.co/"),
    ],
    "workday": [
        re.compile(r"\.wd1\.myworkdayjobs\.com/"),
        re.compile(r"\.wd5\.myworkdayjobs\.com/"),
        re.compile(r"myworkdayjobs\.com/"),
    ],
}

ATS_DOM_SELECTORS: dict[str, list[str]] = {
    "greenhouse": [
        "#main_application_form",
        'input[name="job_application"]',
    ],
    "lever": [
        'div[data-react-class="ApplicationForm"]',
        ".lever-application-form",
    ],
    "workday": [
        'div[data-automation-id="applicationForm"]',
        'input[data-automation-id*="application"]',
    ],
}

ATS_DIFFICULTY_MAP: dict[str, ATSDifficulty] = {
    "greenhouse": ATSDifficulty.easy_apply,
    "lever": ATSDifficulty.easy_apply,
    "workday": ATSDifficulty.multi_step,
}

CAPTCHA_SELECTORS = [
    "div.captcha",
    "#captcha",
    "iframe[src*='captcha']",
    "div[data-testid='captcha']",
    ".challenge-form",
]


class ATSDetector:
    """Detect ATS platform from URL patterns and DOM inspection."""

    def __init__(self, browser_service: "BrowserService") -> None:
        self._browser_service = browser_service

    def detect_from_url(self, url: str) -> ATSDetectionResult | None:
        """Phase 1: URL pattern matching (instant, no browser needed)."""
        for platform, patterns in ATS_URL_PATTERNS.items():
            for pattern in patterns:
                if pattern.search(url):
                    difficulty = ATS_DIFFICULTY_MAP.get(platform, ATSDifficulty.manual_only)
                    return ATSDetectionResult(
                        ats_platform=platform,
                        detection_method="url_pattern",
                        apply_url=url,
                        confidence=1.0,
                        difficulty=difficulty,
                    )
        return None

    async def detect_from_page(self, page: "Page", url: str) -> ATSDetectionResult:
        """Phase 2: DOM inspection for ATS platform identification."""
        start = time.monotonic()

        for selector in CAPTCHA_SELECTORS:
            captcha = await page.query_selector(selector)
            if captcha:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return ATSDetectionResult(
                    ats_platform=None,
                    detection_method="dom_inspection",
                    apply_url=url,
                    difficulty=ATSDifficulty.manual_only,
                    confidence=0.0,
                    error="CAPTCHA detected",
                    detection_time_ms=elapsed_ms,
                )

        for platform, selectors in ATS_DOM_SELECTORS.items():
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    difficulty = ATS_DIFFICULTY_MAP.get(platform, ATSDifficulty.manual_only)
                    fields = await self.extract_form_fields(page)
                    elapsed_ms = int((time.monotonic() - start) * 1000)
                    return ATSDetectionResult(
                        ats_platform=platform,
                        detection_method="dom_inspection",
                        apply_url=url,
                        form_url=page.url,
                        detected_fields=fields,
                        difficulty=difficulty,
                        confidence=0.9,
                        detection_time_ms=elapsed_ms,
                    )

        fields = await self.extract_form_fields(page)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return ATSDetectionResult(
            ats_platform="generic",
            detection_method="dom_inspection",
            apply_url=url,
            form_url=page.url,
            detected_fields=fields,
            difficulty=ATSDifficulty.manual_assist,
            confidence=0.55,
            detection_time_ms=elapsed_ms,
        )

    async def detect(self, apply_url: str) -> ATSDetectionResult:
        """Full detection pipeline: URL patterns first, then DOM inspection."""
        start = time.monotonic()

        is_valid, error = validate_apply_url(apply_url)
        if not is_valid:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return ATSDetectionResult(
                ats_platform=None,
                detection_method="failed",
                apply_url=apply_url,
                difficulty=ATSDifficulty.manual_only,
                confidence=0.0,
                error=error,
                detection_time_ms=elapsed_ms,
            )

        url_result = self.detect_from_url(apply_url)
        if url_result is not None:
            url_result.detection_time_ms = int((time.monotonic() - start) * 1000)
            return url_result

        page = await self._browser_service.new_page()
        try:
            response = await self._browser_service.safe_goto(page, apply_url)
            if response is None:
                elapsed_ms = int((time.monotonic() - start) * 1000)
                return ATSDetectionResult(
                    ats_platform=None,
                    detection_method="failed",
                    apply_url=apply_url,
                    difficulty=ATSDifficulty.manual_only,
                    confidence=0.0,
                    error="Failed to navigate to URL",
                    detection_time_ms=elapsed_ms,
                )

            await self._browser_service.random_delay()

            result = await self.detect_from_page(page, apply_url)

            screenshot_name = f"detection_{int(time.time())}"
            try:
                screenshot_path = await self._browser_service.capture_screenshot(page, screenshot_name)
                result.screenshot_path = screenshot_path
            except Exception as exc:
                logger.warning(f"Screenshot capture failed: {exc}")

            result.detection_time_ms = int((time.monotonic() - start) * 1000)
            return result

        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            logger.error(f"ATS detection failed for {apply_url}: {exc}", exc_info=True)
            return ATSDetectionResult(
                ats_platform=None,
                detection_method="failed",
                apply_url=apply_url,
                difficulty=ATSDifficulty.manual_only,
                confidence=0.0,
                error=str(exc),
                detection_time_ms=elapsed_ms,
            )
        finally:
            await self._browser_service.close_page(page)

    async def extract_form_fields(self, page: "Page") -> list[str]:
        """Extract visible form field names/labels from the page."""
        fields: list[str] = []
        try:
            inputs = await page.query_selector_all("input[name], select[name], textarea[name]")
            for element in inputs:
                name = await element.get_attribute("name")
                if name:
                    fields.append(name)
        except Exception:
            pass
        return fields
