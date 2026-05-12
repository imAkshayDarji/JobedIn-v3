"""LinkedIn Easy Apply and external redirect apply handler.

Handles two LinkedIn apply flows:
1. Easy Apply: In-LI form with name, email, phone, resume upload
2. External Apply: Redirect to employer site, use generic form detector

This service is invoked at apply-time (not ingestion-time) because LinkedIn
requires the user's authenticated session.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import settings
from app.models.base import ApplicationStatus

logger = logging.getLogger(__name__)

EASY_APPLY_SELECTORS = [
    "button[data-control-name='easy_apply_button']",
    "button.jobs-apply-button",
    "button:has-text('Easy Apply')",
    "button:has-text('Apply now')",
    "button:has-text('Apply')",
]

EXTERNAL_APPLY_SELECTORS = [
    "button[data-control-name='apply_button']",
    "a[data-control-name='apply_button']",
    "button:has-text('Apply')",
    "a.apply-button",
]

CAPTCHA_SELECTORS = [
    "div.captcha",
    "#captcha",
    "iframe[src*='captcha']",
    "div[data-testid='captcha']",
    ".challenge-form",
]

MAX_FORM_STEPS = 5


class LinkedInAutoApply:
    """Handle LinkedIn Easy Apply and external redirect apply."""

    def __init__(self, browser_service: Any) -> None:
        self._browser = browser_service

    async def apply(self, job: Any, profile: Any, resume_path: str) -> dict[str, Any]:
        """Main entry: attempt LinkedIn apply for the given job.

        Flow:
        1. Check user has LinkedIn credentials
        2. Login via LinkedInDiscovery
        3. Navigate to job URL
        4. Try Easy Apply button
        5. Try external Apply button (redirect to employer)
        6. Fall back to manual_required
        """
        credentials = self._get_credentials(profile)
        if not credentials:
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": job.source_url,
                "notes": "No LinkedIn credentials stored. Add LinkedIn email and password in your profile.",
            }

        from app.services.job_sources.linkedin import LinkedInDiscovery
        from app.services.job_sources.exceptions import LinkedInCAPTCHAError, LinkedInAuthError

        source_url = (job.source_url or "").strip()
        if not source_url:
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": None,
                "notes": "No LinkedIn URL for this job.",
            }

        try:
            async with LinkedInDiscovery(headless=settings.ATS_DETECT_HEADLESS) as li:
                await li.login(credentials["email"], credentials["password"])

                page = await self._browser.new_page()
                try:
                    resp = await self._browser.safe_goto(page, source_url)
                    if resp is None:
                        return {
                            "status": ApplicationStatus.manual_required,
                            "manual_url": source_url,
                            "notes": "Could not navigate to LinkedIn job page.",
                        }

                    await self._browser.random_delay(1.0, 2.0)

                    for sel in CAPTCHA_SELECTORS:
                        captcha = await page.query_selector(sel)
                        if captcha:
                            return {
                                "status": ApplicationStatus.manual_required,
                                "manual_url": source_url,
                                "notes": "LinkedIn CAPTCHA detected. Please apply manually.",
                            }

                    easy_result = await self._try_easy_apply(page, profile, resume_path)
                    if easy_result:
                        return easy_result

                    external_result = await self._try_external_apply(page, profile, resume_path)
                    if external_result:
                        return external_result

                    return {
                        "status": ApplicationStatus.manual_required,
                        "manual_url": source_url,
                        "notes": "No Easy Apply or external apply button found on LinkedIn job page.",
                    }

                finally:
                    await self._browser.close_page(page)

        except LinkedInCAPTCHAError as exc:
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": source_url,
                "notes": f"LinkedIn CAPTCHA: {exc}",
            }
        except LinkedInAuthError as exc:
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": source_url,
                "notes": f"LinkedIn auth failed: {exc}. Update your LinkedIn credentials.",
            }
        except Exception as exc:
            logger.error(f"LinkedIn apply error: {exc}", exc_info=True)
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": source_url,
                "notes": f"LinkedIn apply error: {exc}",
            }

    async def _try_easy_apply(
        self, page: Any, profile: Any, resume_path: str
    ) -> dict[str, Any] | None:
        """Try to find and use the Easy Apply button."""
        for selector in EASY_APPLY_SELECTORS:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible(timeout=2000):
                    await button.click()
                    await self._browser.random_delay(1.0, 2.0)

                    result = await self._fill_easy_apply_form(page, profile, resume_path)
                    return result
            except Exception:
                continue

        return None

    async def _fill_easy_apply_form(
        self, page: Any, profile: Any, resume_path: str
    ) -> dict[str, Any]:
        """Fill the multi-step Easy Apply form."""
        steps_completed = 0

        while steps_completed < MAX_FORM_STEPS:
            steps_completed += 1

            # Try to fill text inputs
            text_inputs = page.locator("input[type='text'], input:not([type])")
            count = await text_inputs.count()
            for i in range(count):
                try:
                    inp = text_inputs.nth(i)
                    if not await inp.is_visible(timeout=500):
                        continue
                    label_text = ""
                    label = await page.query_selector(f"label[for='{await inp.get_attribute('id') or ''}']")
                    if label:
                        label_text = (await label.inner_text()).lower()

                    value = self._map_field_to_profile(label_text, profile)
                    if value:
                        await inp.fill(value)
                except Exception:
                    continue

            # Try to fill email
            try:
                email_input = page.locator("input[type='email']")
                if await email_input.count() > 0:
                    email = getattr(profile, "linkedin_email", None) or ""
                    if email:
                        await email_input.first.fill(email)
            except Exception:
                pass

            # Try to fill phone
            try:
                phone_input = page.locator("input[type='tel']")
                if await phone_input.count() > 0:
                    phone = getattr(profile, "phone", None) or ""
                    if phone:
                        await phone_input.first.fill(phone)
            except Exception:
                pass

            # Try to upload resume
            try:
                file_input = page.locator("input[type='file']")
                if await file_input.count() > 0:
                    await file_input.first.set_input_files(resume_path)
                    await self._browser.random_delay(0.5, 1.0)
            except Exception:
                pass

            # Try to click Next/Review/Submit
            next_clicked = False
            for btn_text in ["Next", "Review", "Submit", "Submit application"]:
                try:
                    btn = page.locator(f"button:has-text('{btn_text}')")
                    if await btn.count() > 0 and await btn.first.is_visible(timeout=500):
                        await btn.first.click()
                        await self._browser.random_delay(0.5, 1.5)
                        next_clicked = True
                        break
                except Exception:
                    continue

            if not next_clicked:
                break

            # Check if we got a confirmation
            try:
                confirmation = page.locator("text=Application submitted, text=You've already applied")
                if await confirmation.count() > 0:
                    screenshot_path = await self._browser.capture_screenshot(page, "li_easy_apply_success")
                    return {
                        "status": ApplicationStatus.applied,
                        "screenshot_path": screenshot_path,
                    }
            except Exception:
                pass

        screenshot_path = await self._browser.capture_screenshot(page, "li_easy_apply_partial")

        return {
            "status": ApplicationStatus.applied_with_issues,
            "screenshot_path": screenshot_path,
            "manual_url": page.url,
            "notes": "LinkedIn Easy Apply partially completed. Review and finish manually.",
        }

    async def _try_external_apply(
        self, page: Any, profile: Any, resume_path: str
    ) -> dict[str, Any] | None:
        """Try to find and follow the external Apply button."""
        for selector in EXTERNAL_APPLY_SELECTORS:
            try:
                button = await page.query_selector(selector)
                if button and await button.is_visible(timeout=2000):
                    href = await button.get_attribute("href")
                    if href:
                        from app.services.generic_form_detector import GenericFormDetector

                        detector = GenericFormDetector(self._browser)
                        ext_page = await self._browser.new_page()
                        try:
                            resp = await self._browser.safe_goto(ext_page, href)
                            if resp is None:
                                continue

                            await self._browser.random_delay(0.5, 1.0)
                            fields = await detector.detect_fields(ext_page)
                            fill_result = await detector.fill_fields(
                                ext_page, profile, fields, resume_path,
                                "li_external_apply",
                            )

                            screenshot_path = fill_result.screenshot_path
                            submitted = await detector.try_submit(ext_page)

                            if submitted:
                                return {
                                    "status": ApplicationStatus.applied_with_issues,
                                    "screenshot_path": screenshot_path,
                                    "manual_url": href,
                                    "notes": "Submitted via LinkedIn external redirect.",
                                }

                            return {
                                "status": ApplicationStatus.manual_required,
                                "screenshot_path": screenshot_path,
                                "manual_url": href,
                                "notes": "Partially filled external application. Complete manually.",
                            }
                        finally:
                            await self._browser.close_page(ext_page)
                    else:
                        await button.click()
                        await self._browser.random_delay(1.0, 2.0)

                        new_url = page.url
                        if "linkedin.com" not in new_url:
                            return {
                                "status": ApplicationStatus.manual_required,
                                "manual_url": new_url,
                                "notes": "LinkedIn redirected to external site. Apply manually.",
                            }
            except Exception:
                continue

        return None

    def _get_credentials(self, profile: Any) -> dict[str, str] | None:
        """Extract LinkedIn credentials from the candidate profile."""
        email = getattr(profile, "linkedin_email", None)
        encrypted_pw = getattr(profile, "linkedin_password_encrypted", None)

        if not email or not encrypted_pw:
            return None

        try:
            from app.services.credential_crypto import decrypt_value

            password = decrypt_value(encrypted_pw)
            if not password:
                return None
            return {"email": email, "password": password}
        except Exception:
            logger.warning("Failed to decrypt LinkedIn password")
            return None

    def _map_field_to_profile(self, label: str, profile: Any) -> str:
        """Map a form field label to the corresponding profile value."""
        label_lower = label.lower().strip()

        field_map = {
            "first name": "first_name",
            "last name": "last_name",
            "full name": None,
            "name": None,
            "email": "linkedin_email",
            "e-mail": "linkedin_email",
            "phone": "phone",
            "mobile": "phone",
            "location": "location",
            "city": "location",
        }

        for key, attr in field_map.items():
            if key in label_lower:
                if attr is None:
                    if "full" in label_lower or (not label_lower.startswith("first") and not label_lower.startswith("last")):
                        return f"{getattr(profile, 'first_name', '')} {getattr(profile, 'last_name', '')}".strip()
                    continue
                val = getattr(profile, attr, None)
                return val or ""

        return ""
