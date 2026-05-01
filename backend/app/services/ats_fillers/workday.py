from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING

from app.services.ats_fillers import ATSFiller
from app.services.ats_fillers.base_filler import BaseATSFiller, MAX_ENTRIES
from app.services.ats_fillers.exceptions import (
    ApplyResult,
    ATSSubmitError,
    ATSTimeoutError,
    FieldResult,
    FillResult,
)

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.models.candidate import CandidateProfile
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)

_WORKDAY_STEP_TIMEOUT_MS = 30000
_WORKDAY_TOTAL_TIMEOUT_S = 180


class WorkdayFiller(ATSFiller):
    """Workday ATS form filler.

    Workday is the most complex: multi-page wizard with 5+ steps.
    All selectors use data-automation-id attributes.
    Must navigate between steps with page.wait_for_load_state between each.
    Timeout: 180s (vs 60s for single-page fillers).
    """

    SELECTORS: dict[str, str] = {
        "form_container": 'div[data-automation-id="applicationForm"]',
        "first_name": 'input[data-automation-id="firstName"]',
        "last_name": 'input[data-automation-id="lastName"]',
        "email": 'input[data-automation-id="email"]',
        "phone": 'input[data-automation-id="phone"]',
        "resume": 'input[data-automation-id="resume"]',
        "experience_company": 'input[data-automation-id="companyName_{i}"]',
        "experience_title": 'input[data-automation-id="jobTitle_{i}"]',
        "experience_description": 'textarea[data-automation-id="jobDescription_{i}"]',
        "education_institution": 'input[data-automation-id="schoolName_{i}"]',
        "education_degree": 'input[data-automation-id="degree_{i}"]',
        "education_field": 'input[data-automation-id="fieldOfStudy_{i}"]',
        "next_button": 'button[data-automation-id="next"]',
        "submit_button": 'button[data-automation-id="submit"]',
        "confirm_container": 'div[data-automation-id="confirmation"]',
        "confirm_text": 'text="Application Submitted"',
        "dialog_leave": 'button[data-automation-id="leaveButton"]',
    }

    def __init__(self, browser_service: BrowserService) -> None:
        self._base = BaseATSFiller(browser_service)
        self._browser_service = browser_service

    async def can_handle(self, page: Page) -> bool:
        for selector in [
            'div[data-automation-id="applicationForm"]',
            'input[data-automation-id*="application"]',
        ]:
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
        start = time.monotonic()
        filled: list[FieldResult] = []
        skipped: list[FieldResult] = []
        sel = self.SELECTORS

        # Step 1: Personal info
        name_results = await self._base.fill_name_fields(
            page, profile, sel["first_name"], sel["last_name"],
        )
        for r in name_results:
            (filled if r.success else skipped).append(r)

        contact_results = await self._base.fill_contact_fields(
            page, profile,
            email_selector=sel["email"],
            phone_selector=sel["phone"],
            location_selector=None,
        )
        for r in contact_results:
            (filled if r.success else skipped).append(r)

        await self._navigate_next(page)
        self._check_timeout(start)

        # Step 2: Resume upload
        if resume_path:
            result = await self._base.upload_file(page, sel["resume"], "resume", resume_path)
            (filled if result.success else skipped).append(result)
        else:
            skipped.append(FieldResult(selector=sel["resume"], field_name="resume", success=False, error="no_resume_path"))

        await self._navigate_next(page)
        self._check_timeout(start)

        # Step 3: Experience (up to MAX_ENTRIES)
        if hasattr(profile, "experience") and profile.experience:
            exp_selectors = {
                "company": sel["experience_company"],
                "title": sel["experience_title"],
                "description": sel["experience_description"],
            }
            for i in range(min(len(profile.experience), MAX_ENTRIES)):
                exp_results = await self._base.fill_experience_fields(page, profile.experience, exp_selectors, i)
                for r in exp_results:
                    (filled if r.success else skipped).append(r)

        await self._navigate_next(page)
        self._check_timeout(start)

        # Step 4: Education (up to MAX_ENTRIES)
        if hasattr(profile, "education") and profile.education:
            edu_selectors = {
                "institution": sel["education_institution"],
                "degree": sel["education_degree"],
                "field_of_study": sel["education_field"],
            }
            for i in range(min(len(profile.education), MAX_ENTRIES)):
                edu_results = await self._base.fill_education_fields(page, profile.education, edu_selectors, i)
                for r in edu_results:
                    (filled if r.success else skipped).append(r)

        await self._navigate_next(page)
        self._check_timeout(start)

        logger.info(
            "workday_fill_complete",
            extra={"filled": len(filled), "skipped": len(skipped)},
        )

        return FillResult(filled=filled, skipped=skipped)

    async def submit(self, page: Page) -> bool:
        submit_btn = await page.query_selector(self.SELECTORS["submit_button"])
        if submit_btn is None:
            raise ATSSubmitError("Submit button not found on Workday form")

        await submit_btn.click()
        await page.wait_for_load_state("networkidle")
        return True

    async def verify(self, page: Page) -> ApplyResult:
        screenshot_name = f"workday_verify_{int(time.time())}"
        screenshot_path = await self._base.wait_and_screenshot(page, screenshot_name)

        confirm_container = await page.query_selector(self.SELECTORS["confirm_container"])
        if confirm_container is not None:
            return ApplyResult(
                success=True,
                platform="workday",
                message="Application submitted successfully",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        confirm_text = await page.query_selector(self.SELECTORS["confirm_text"])
        if confirm_text is not None:
            return ApplyResult(
                success=True,
                platform="workday",
                message="Application submitted successfully (confirmation text found)",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        return ApplyResult(
            success=False,
            platform="workday",
            message="Could not confirm submission",
            screenshot_path=screenshot_path,
        )

    async def _navigate_next(self, page: Page) -> None:
        next_btn = await page.query_selector(self.SELECTORS["next_button"])
        if next_btn is not None:
            await next_btn.click()
            await page.wait_for_load_state("networkidle")
            await asyncio.sleep(0.5)

            dialog_btn = await page.query_selector(self.SELECTORS["dialog_leave"])
            if dialog_btn is not None:
                await dialog_btn.click()
                await page.wait_for_load_state("networkidle")

    def _check_timeout(self, start: float) -> None:
        elapsed = time.monotonic() - start
        if elapsed > _WORKDAY_TOTAL_TIMEOUT_S:
            raise ATSTimeoutError(f"Workday fill exceeded {_WORKDAY_TOTAL_TIMEOUT_S}s timeout")
