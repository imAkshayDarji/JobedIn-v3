from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from app.services.ats_fillers import ATSFiller
from app.services.ats_fillers.base_filler import BaseATSFiller, MAX_ENTRIES
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


class GreenhouseFiller(ATSFiller):
    """Greenhouse ATS form filler.

    Greenhouse forms are single-page with well-known selectors.
    Strategy: fill all known fields, auto-decline EEO fields, skip unknown custom questions.
    """

    SELECTORS: dict[str, str] = {
        "first_name": "#first_name",
        "last_name": "#last_name",
        "email": "#email",
        "phone": "#phone",
        "address": "#address",
        "city": "#city",
        "state": "#state",
        "zip_code": "#zip_code",
        "country": "#country_dropdown",
        "resume": "input[type='file']#resume",
        "cover_letter": "textarea#cover_letter",
        "submit": "#submit_app",
        "confirm_text": "text='You have successfully applied'",
        "confirm_url": "/confirmation",
        "eeo_gender": "select#job_application_answers_attributes_0_question_id",
        "eeo_race": "select#job_application_answers_attributes_1_question_id",
        "eeo_veteran": "select#job_application_answers_attributes_2_question_id",
        "eeo_disability": "select#job_application_answers_attributes_3_question_id",
        "education_institution": "#education_section_school_name_{i}",
        "education_degree": "#education_section_degree_{i}",
        "education_field": "#education_section_field_of_study_{i}",
        "experience_company": "#experience_section_company_name_{i}",
        "experience_title": "#experience_section_title_{i}",
        "experience_description": "#experience_section_description_{i}",
    }

    EEO_DECLINE_OPTIONS = [
        "Decline to Self-Identify",
        "I don't wish to answer",
        "I decline to self identify",
        "Prefer not to say",
    ]

    def __init__(self, browser_service: BrowserService) -> None:
        self._base = BaseATSFiller(browser_service)
        self._browser_service = browser_service

    async def can_handle(self, page: Page) -> bool:
        for selector in ["#main_application_form", 'input[name="job_application"]']:
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

        if profile.location:
            address_parts = profile.location.split(",")
            if address_parts:
                result = await self._base.fill_text_field(page, sel["address"], "address", address_parts[0].strip())
                (filled if result.success else skipped).append(result)

        if profile.location and "," in profile.location:
            city_part = profile.location.split(",")[0].strip()
            result = await self._base.fill_text_field(page, sel["city"], "city", city_part)
            (filled if result.success else skipped).append(result)

        if resume_path:
            result = await self._base.upload_file(page, sel["resume"], "resume", resume_path)
            (filled if result.success else skipped).append(result)
        else:
            skipped.append(FieldResult(selector=sel["resume"], field_name="resume", success=False, error="no_resume_path"))

        cover_letter_result = await self._base.fill_text_field(page, sel["cover_letter"], "cover_letter", "")
        (filled if cover_letter_result.success else skipped).append(cover_letter_result)

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

        eeo_selectors = [sel["eeo_gender"], sel["eeo_race"], sel["eeo_veteran"], sel["eeo_disability"]]
        for eeo_sel in eeo_selectors:
            element = await page.query_selector(eeo_sel)
            if element is not None:
                result = await self._auto_decline_eeo(page, eeo_sel)
                (filled if result.success else skipped).append(result)

        logger.info(
            "greenhouse_fill_complete",
            extra={"filled": len(filled), "skipped": len(skipped)},
        )

        return FillResult(filled=filled, skipped=skipped)

    async def submit(self, page: Page) -> bool:
        submit_btn = await page.query_selector(self.SELECTORS["submit"])
        if submit_btn is None:
            submit_btn = await page.query_selector("button[type='submit']")

        if submit_btn is None:
            submit_btn = await page.query_selector("input[type='submit']")

        if submit_btn is None:
            submit_btn = await page.query_selector("#submit_app")

        if submit_btn is None:
            raise ATSSubmitError("Submit button not found on Greenhouse form")

        await submit_btn.click()
        await page.wait_for_load_state("networkidle")
        return True

    async def verify(self, page: Page) -> ApplyResult:
        screenshot_name = f"greenhouse_verify_{int(time.time())}"
        screenshot_path = await self._base.wait_and_screenshot(page, screenshot_name)

        confirmation = await page.query_selector(self.SELECTORS["confirm_text"])
        if confirmation is not None:
            return ApplyResult(
                success=True,
                platform="greenhouse",
                message="Application submitted successfully",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        current_url = page.url
        if self.SELECTORS["confirm_url"] in current_url:
            return ApplyResult(
                success=True,
                platform="greenhouse",
                message="Application submitted successfully (confirmation URL)",
                screenshot_path=screenshot_path,
                submitted_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            )

        return ApplyResult(
            success=False,
            platform="greenhouse",
            message="Could not confirm submission",
            screenshot_path=screenshot_path,
        )

    async def _auto_decline_eeo(self, page: Page, selector: str) -> FieldResult:
        for option_text in self.EEO_DECLINE_OPTIONS:
            try:
                element = await page.query_selector(selector)
                if element is None:
                    return FieldResult(selector=selector, field_name="eeo", success=False, error="element_not_found")

                await element.select_option(label=option_text)
                logger.info("field_filled", extra={"field_name": "eeo_auto_decline", "success": True})
                return FieldResult(selector=selector, field_name="eeo_auto_decline", success=True)
            except Exception:
                continue

        return FieldResult(selector=selector, field_name="eeo_auto_decline", success=False, error="no_decline_option_found")
