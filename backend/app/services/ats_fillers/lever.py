from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.services.ats_fillers import ATSFiller
from app.services.ats_fillers.base_filler import BaseATSFiller
from app.services.ats_fillers.exceptions import (
    ApplyResult,
    ATSSubmitError,
    FieldResult,
    FillResult,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.models.candidate import CandidateProfile
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)


class LeverFiller(ATSFiller):
    """Lever ATS form filler.

    Lever forms are the simplest: single page, React-rendered, fewer custom questions.
    """

    SELECTORS: dict[str, str] = {
        "name": "#application-name",
        "email": "#application-email",
        "phone": "#application-phone",
        "org": "#application-org",
        "resume": "input[type='file']#application-resume",
        "cover_letter": "textarea#application-cover-letter",
        "linkedin": "#application-links-LinkedIn",
        "github": "#application-links-GitHub",
        "portfolio": "#application-links-Portfolio",
        "website": "#application-links-Website",
        "submit": "button[type='submit']",
        "submit_alt": ".btn-submit",
        "confirm_class": ".application-complete",
        "confirm_url_thanks": "/thanks",
        "confirm_url_applied": "/applied",
    }

    def __init__(self, browser_service: BrowserService) -> None:
        self._base = BaseATSFiller(browser_service)
        self._browser_service = browser_service

    async def can_handle(self, page: Page) -> bool:
        for selector in ['div[data-react-class="ApplicationForm"]', ".lever-application-form"]:
            element = await page.query_selector(selector)
            if element is not None:
                return True
        return False

    async def fill(
        self,
        page: Page,
        profile: CandidateProfile,
        resume_path: str | None = None,
    ) -> FillResult:
        filled: list[FieldResult] = []
        skipped: list[FieldResult] = []
        sel = self.SELECTORS

        full_name = f"{profile.first_name} {profile.last_name}".strip()
        if full_name:
            result = await self._base.fill_text_field(page, sel["name"], "name", full_name)
            (filled if result.success else skipped).append(result)
        else:
            skipped.append(FieldResult(selector=sel["name"], field_name="name", success=False, error="no_value"))

        contact_results = await self._base.fill_contact_fields(
            page, profile,
            email_selector=sel["email"],
            phone_selector=sel["phone"],
            location_selector=None,
        )
        for r in contact_results:
            (filled if r.success else skipped).append(r)

        if resume_path:
            result = await self._base.upload_file(page, sel["resume"], "resume", resume_path)
            (filled if result.success else skipped).append(result)
        else:
            skipped.append(FieldResult(selector=sel["resume"], field_name="resume", success=False, error="no_resume_path"))

        url_fields = [
            ("linkedin", "linkedin_url", sel["linkedin"]),
            ("github", "github_url", sel["github"]),
            ("portfolio", "portfolio_url", sel["portfolio"]),
            ("website", "website_url", sel["website"]),
        ]
        for field_name, profile_attr, selector in url_fields:
            value = getattr(profile, profile_attr, None)
            if value:
                result = await self._base.fill_text_field(page, selector, field_name, value)
                (filled if result.success else skipped).append(result)

        logger.info(
            "lever_fill_complete",
            extra={"filled": len(filled), "skipped": len(skipped)},
        )

        return FillResult(filled=filled, skipped=skipped)

    async def submit(self, page: Page) -> bool:
        submit_btn = await page.query_selector(self.SELECTORS["submit"])
        if submit_btn is None:
            submit_btn = await page.query_selector(self.SELECTORS["submit_alt"])

        if submit_btn is None:
            raise ATSSubmitError("Submit button not found on Lever form")

        await submit_btn.click()
        await page.wait_for_load_state("networkidle")
        return True

    async def verify(self, page: Page) -> ApplyResult:
        screenshot_name = f"lever_verify_{int(time.time())}"
        screenshot_path = await self._base.wait_and_screenshot(page, screenshot_name)

        confirmation = await page.query_selector(self.SELECTORS["confirm_class"])
        if confirmation is not None:
            return ApplyResult(
                success=True,
                platform="lever",
                message="Application submitted successfully",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        current_url = page.url
        if self.SELECTORS["confirm_url_thanks"] in current_url or self.SELECTORS["confirm_url_applied"] in current_url:
            return ApplyResult(
                success=True,
                platform="lever",
                message="Application submitted successfully (confirmation URL)",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        return ApplyResult(
            success=False,
            platform="lever",
            message="Could not confirm submission",
            screenshot_path=screenshot_path,
        )
