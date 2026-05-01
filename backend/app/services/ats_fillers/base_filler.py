import asyncio
import logging
import random
import re
from pathlib import Path
from typing import TYPE_CHECKING

from app.config import settings
from app.services.ats_fillers.exceptions import ATSFormError, FieldResult

if TYPE_CHECKING:
    from playwright.async_api import Page

    from app.models.candidate import CandidateProfile
    from app.models.education import Education
    from app.models.experience import Experience
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)

MAX_ENTRIES = 3

_TYPING_DELAY_MIN_MS = 30
_TYPING_DELAY_MAX_MS = 80


class BaseATSFiller:
    """Plain utility class with shared helpers for ATS form filling.

    Concrete fillers (Greenhouse, Lever, Workday) extend ATSFiller ABC
    and instantiate this class to use its helper methods.
    """

    def __init__(self, browser_service: "BrowserService") -> None:
        self._browser_service = browser_service

    async def fill_text_field(
        self,
        page: "Page",
        selector: str,
        field_name: str,
        value: str,
    ) -> FieldResult:
        try:
            element = await page.query_selector(selector)
            if element is None:
                logger.info("field_skipped", extra={"field_name": field_name, "reason": "element_not_found"})
                return FieldResult(selector=selector, field_name=field_name, success=False, error="element_not_found")

            await element.click()
            await element.fill("")
            for char in value:
                await element.type(char, delay=random.randint(_TYPING_DELAY_MIN_MS, _TYPING_DELAY_MAX_MS))

            logger.info("field_filled", extra={"field_name": field_name, "success": True})
            return FieldResult(selector=selector, field_name=field_name, success=True)

        except Exception as exc:
            logger.warning("field_fill_failed", extra={"field_name": field_name, "error": str(exc)})
            await self._capture_failure_screenshot(page, field_name)
            return FieldResult(selector=selector, field_name=field_name, success=False, error=str(exc))

    async def select_dropdown(
        self,
        page: "Page",
        selector: str,
        field_name: str,
        value: str,
    ) -> FieldResult:
        try:
            element = await page.query_selector(selector)
            if element is None:
                logger.info("field_skipped", extra={"field_name": field_name, "reason": "element_not_found"})
                return FieldResult(selector=selector, field_name=field_name, success=False, error="element_not_found")

            await element.select_option(label=value)
            logger.info("field_filled", extra={"field_name": field_name, "success": True})
            return FieldResult(selector=selector, field_name=field_name, success=True)

        except Exception as exc:
            logger.warning("field_fill_failed", extra={"field_name": field_name, "error": str(exc)})
            await self._capture_failure_screenshot(page, field_name)
            return FieldResult(selector=selector, field_name=field_name, success=False, error=str(exc))

    async def upload_file(
        self,
        page: "Page",
        selector: str,
        field_name: str,
        file_path: str,
    ) -> FieldResult:
        try:
            resume_dir = Path(settings.ATS_RESUME_DIR).resolve()
            resolved = Path(file_path).resolve()

            if not str(resolved).startswith(str(resume_dir)):
                raise ATSFormError(f"Path traversal blocked: {file_path}")

            element = await page.query_selector(selector)
            if element is None:
                logger.info("field_skipped", extra={"field_name": field_name, "reason": "element_not_found"})
                return FieldResult(selector=selector, field_name=field_name, success=False, error="element_not_found")

            await element.set_input_files(str(resolved))
            logger.info("field_filled", extra={"field_name": field_name, "success": True})
            return FieldResult(selector=selector, field_name=field_name, success=True)

        except ATSFormError:
            raise
        except Exception as exc:
            logger.warning("field_fill_failed", extra={"field_name": field_name, "error": str(exc)})
            await self._capture_failure_screenshot(page, field_name)
            return FieldResult(selector=selector, field_name=field_name, success=False, error=str(exc))

    async def check_checkbox(
        self,
        page: "Page",
        selector: str,
        field_name: str,
    ) -> FieldResult:
        try:
            element = await page.query_selector(selector)
            if element is None:
                logger.info("field_skipped", extra={"field_name": field_name, "reason": "element_not_found"})
                return FieldResult(selector=selector, field_name=field_name, success=False, error="element_not_found")

            is_checked = await element.is_checked()
            if not is_checked:
                await element.click()

            logger.info("field_filled", extra={"field_name": field_name, "success": True})
            return FieldResult(selector=selector, field_name=field_name, success=True)

        except Exception as exc:
            logger.warning("field_fill_failed", extra={"field_name": field_name, "error": str(exc)})
            await self._capture_failure_screenshot(page, field_name)
            return FieldResult(selector=selector, field_name=field_name, success=False, error=str(exc))

    async def fill_name_fields(
        self,
        page: "Page",
        profile: "CandidateProfile",
        first_name_selector: str,
        last_name_selector: str,
    ) -> list[FieldResult]:
        results: list[FieldResult] = []

        if profile.first_name:
            results.append(await self.fill_text_field(page, first_name_selector, "first_name", profile.first_name))
        else:
            results.append(FieldResult(selector=first_name_selector, field_name="first_name", success=False, error="no_value"))

        if profile.last_name:
            results.append(await self.fill_text_field(page, last_name_selector, "last_name", profile.last_name))
        else:
            results.append(FieldResult(selector=last_name_selector, field_name="last_name", success=False, error="no_value"))

        return results

    async def fill_contact_fields(
        self,
        page: "Page",
        profile: "CandidateProfile",
        email_selector: str | None = None,
        phone_selector: str | None = None,
        location_selector: str | None = None,
    ) -> list[FieldResult]:
        results: list[FieldResult] = []

        if email_selector and hasattr(profile, "linkedin_email") and profile.linkedin_email:
            results.append(await self.fill_text_field(page, email_selector, "email", profile.linkedin_email))
        elif email_selector:
            results.append(FieldResult(selector=email_selector, field_name="email", success=False, error="no_value"))

        if phone_selector and profile.phone:
            normalized = normalize_phone(profile.phone)
            results.append(await self.fill_text_field(page, phone_selector, "phone", normalized))
        elif phone_selector:
            results.append(FieldResult(selector=phone_selector, field_name="phone", success=False, error="no_value"))

        if location_selector and profile.location:
            results.append(await self.fill_text_field(page, location_selector, "location", profile.location))
        elif location_selector:
            results.append(FieldResult(selector=location_selector, field_name="location", success=False, error="no_value"))

        return results

    async def fill_education_fields(
        self,
        page: "Page",
        education_list: list["Education"],
        selectors: dict[str, str],
        index: int = 0,
    ) -> list[FieldResult]:
        results: list[FieldResult] = []

        if index >= len(education_list) or index >= MAX_ENTRIES:
            return results

        edu = education_list[index]
        prefix = f"education[{index}]"

        institution_sel = selectors.get("institution", "").replace("{i}", str(index))
        degree_sel = selectors.get("degree", "").replace("{i}", str(index))
        field_of_study_sel = selectors.get("field_of_study", "").replace("{i}", str(index))

        if institution_sel and edu.institution:
            results.append(await self.fill_text_field(page, institution_sel, f"{prefix}.institution", edu.institution))

        if degree_sel and edu.degree:
            results.append(await self.fill_text_field(page, degree_sel, f"{prefix}.degree", edu.degree))

        if field_of_study_sel and edu.field_of_study:
            results.append(await self.fill_text_field(page, field_of_study_sel, f"{prefix}.field_of_study", edu.field_of_study))

        return results

    async def fill_experience_fields(
        self,
        page: "Page",
        experience_list: list["Experience"],
        selectors: dict[str, str],
        index: int = 0,
    ) -> list[FieldResult]:
        results: list[FieldResult] = []

        if index >= len(experience_list) or index >= MAX_ENTRIES:
            return results

        exp = experience_list[index]
        prefix = f"experience[{index}]"

        company_sel = selectors.get("company", "").replace("{i}", str(index))
        title_sel = selectors.get("title", "").replace("{i}", str(index))
        description_sel = selectors.get("description", "").replace("{i}", str(index))

        if company_sel and exp.company:
            results.append(await self.fill_text_field(page, company_sel, f"{prefix}.company", exp.company))

        if title_sel and exp.title:
            results.append(await self.fill_text_field(page, title_sel, f"{prefix}.title", exp.title))

        if description_sel and exp.description:
            results.append(await self.fill_text_field(page, description_sel, f"{prefix}.description", exp.description))

        return results

    async def wait_and_screenshot(self, page: "Page", name: str) -> str:
        await page.wait_for_load_state("networkidle")
        return await self._browser_service.capture_screenshot(page, name)

    async def _capture_failure_screenshot(self, page: "Page", field_name: str) -> None:
        try:
            screenshot_name = f"field_fail_{field_name}_{random.randint(1000, 9999)}"
            await self._browser_service.capture_screenshot(page, screenshot_name)
        except Exception:
            pass


def normalize_phone(value: str | None, country: str = "US") -> str:
    if not value:
        return ""

    digits = re.sub(r"[^\d+]", "", value)

    if digits.startswith("+1") and len(digits) == 12:
        return digits[2:]

    if digits.startswith("+") and len(digits) > 4:
        return digits

    digits_only = re.sub(r"\D", "", value)
    if len(digits_only) == 11 and digits_only.startswith("1"):
        return digits_only[1:]

    if len(digits_only) == 10:
        return digits_only

    return digits_only
