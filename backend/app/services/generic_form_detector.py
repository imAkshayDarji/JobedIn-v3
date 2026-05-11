"""Heuristic detection and partial fill for unknown career-site forms."""

from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.config import settings
from app.services.ats_fillers.base_filler import normalize_phone

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

    from app.models.candidate import CandidateProfile
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)

_TYPING_DELAY_MIN_MS = 30
_TYPING_DELAY_MAX_MS = 80


PROFILE_KEYWORDS: list[tuple[str, list[str]]] = [
    ("first_name", ["first", "fname", "given"]),
    ("last_name", ["last", "lname", "family", "surname"]),
    ("full_name", ["full name", "applicant"]),
    ("email", ["email", "e-mail", "mail"]),
    ("phone", ["phone", "tel", "mobile", "cell"]),
    ("linkedin", ["linkedin"]),
    ("github", ["github"]),
    ("portfolio", ["portfolio", "website"]),
    ("city", ["city", "town"]),
    ("state", ["state", "province"]),
    ("country", ["country"]),
    ("zipcode", ["zip", "postal", "postcode"]),
    ("resume_upload", ["resume", "cv", "curriculum"]),
    ("cover_letter_upload", ["cover letter", "coverletter"]),
]


@dataclass
class FormFieldInfo:
    selector: str
    nth: int
    field_type: str
    label: str | None
    placeholder: str | None
    required: bool
    mapped_to: str | None


@dataclass
class FillResult:
    filled_fields: list[str]
    unfilled_required: list[str]
    screenshot_path: str | None


def _normalize_hints(*parts: str | None) -> str:
    return " ".join((p or "").lower() for p in parts if p)


def _map_hints_to_profile(hints: str) -> str | None:
    hints_l = hints.lower()
    for mapped, keywords in PROFILE_KEYWORDS:
        for kw in keywords:
            if kw in hints_l:
                return mapped
    return None


async def _label_for_element(page: Page, el_id: str | None, name: str | None) -> str | None:
    if el_id:

        escaped = el_id.replace('"', '\\"')

        lab = await page.query_selector(f'label[for="{escaped}"]')

        if lab:

            try:

                t = await lab.inner_text()

                return t.strip() if t else None

            except Exception:

                return None

    if name:

        escaped = name.replace('"', '\\"')

        lab2 = await page.query_selector(f'label:has(+ * [name="{escaped}"])')

        if lab2:

            try:

                t2 = await lab2.inner_text()

                return t2.strip() if t2 else None

            except Exception:

                return None

    return None


class GenericFormDetector:
    """Scan generic HTML forms and map fields to CandidateProfile."""

    def __init__(self, browser_service: BrowserService) -> None:
        self._browser = browser_service

    async def detect_fields(self, page: Page) -> list[FormFieldInfo]:
        tag_selectors = (
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), '
            'textarea, select'
        )
        locator = page.locator(tag_selectors)
        total = await locator.count()

        nth_by_selector: dict[str, int] = {}
        out: list[FormFieldInfo] = []

        for i in range(total):
            el = locator.nth(i)

            try:
                if not await el.is_visible(timeout=500):

                    continue
            except Exception:

                continue

            tag = await el.evaluate("e => e.tagName.toLowerCase()")

            inp_type = ((await el.get_attribute("type")) or "text").lower()

            name = await el.get_attribute("name")

            el_id = await el.get_attribute("id")

            placeholder = await el.get_attribute("placeholder")

            aria_label = await el.get_attribute("aria-label")

            required_attr = await el.get_attribute("required")

            req = required_attr is not None

            selector: str | None = None

            if el_id and el_id.strip():

                selector = f"#{el_id.strip()}"

            elif name and name.strip():

                safe_name = name.strip().replace("\\", "\\\\").replace('"', '\\"')

                selector = f'{tag}[name="{safe_name}"]'

            else:

                continue

            nth = nth_by_selector.get(selector, 0)

            nth_by_selector[selector] = nth + 1

            label_text = await _label_for_element(page, el_id.strip() if el_id else None, name.strip() if name else None)

            hint = _normalize_hints(name, placeholder, aria_label, label_text)

            mapped = _map_hints_to_profile(hint)

            if tag == "input" and inp_type == "file" and mapped is None:

                mapped = _map_hints_to_profile(_normalize_hints(placeholder, aria_label, name, label_text))

                if mapped is None:

                    if any(k in hint for k in ("resume", "cv", "upload")):

                        mapped = "resume_upload"

            ft = inp_type if tag == "input" else ("textarea" if tag == "textarea" else "select")

            out.append(
                FormFieldInfo(
                    selector=selector,
                    nth=nth,
                    field_type=ft,
                    label=label_text,
                    placeholder=placeholder,
                    required=req,
                    mapped_to=mapped,
                ),
            )

        return out

    def get_unfilled_required(self, fields: list[FormFieldInfo], filled: list[str]) -> list[str]:
        filled_set = set(filled)

        missing: list[str] = []

        for f in fields:
            if not f.required:

                continue

            label = (f.label or f.placeholder or f.selector).strip() or f.selector

            m = f.mapped_to

            ok = False

            if m and m in filled_set:

                ok = True

            if m == "resume_upload" and "resume_upload" in filled_set:

                ok = True

            if m == "cover_letter_upload" and "cover_letter_upload" in filled_set:

                ok = True

            if not ok:

                missing.append(label)

        return missing

    def _locator(self, page: Page, field: FormFieldInfo) -> Locator:

        return page.locator(field.selector).nth(field.nth)

    async def _type_human(self, loc: Locator, value: str) -> None:

        await loc.click()

        await loc.fill("")

        for char in value:

            await loc.type(char, delay=random.randint(_TYPING_DELAY_MIN_MS, _TYPING_DELAY_MAX_MS))

    async def fill_fields(
        self,
        page: Page,
        profile: CandidateProfile,
        fields: list[FormFieldInfo],
        resume_path: str,
        screenshot_prefix: str,
    ) -> FillResult:
        filled: list[str] = []

        resume_dir = Path(settings.ATS_RESUME_DIR).resolve()

        resolved_resume = Path(resume_path).resolve()

        if not str(resolved_resume).startswith(str(resume_dir)):
            logger.error("generic_form_resume_path_blocked", extra={"path": resume_path})

            screenshot_path = None

            try:
                screenshot_path = await self._browser.capture_screenshot(page, screenshot_prefix)
            except Exception:
                pass

            return FillResult(
                filled_fields=[],
                unfilled_required=[f.label or f.selector for f in fields if f.required],
                screenshot_path=screenshot_path,
            )

        for field in fields:

            loc = self._locator(page, field)

            mapped = field.mapped_to

            if mapped is None:

                continue

            try:
                if not await loc.is_visible(timeout=800):

                    continue
            except Exception:

                continue

            if mapped == "resume_upload":

                if field.field_type == "file":

                    try:

                        await loc.set_input_files(str(resolved_resume))

                        filled.append("resume_upload")

                    except Exception as exc:

                        logger.warning("generic_resume_upload_failed", extra={"error": str(exc)})

                continue

            if mapped == "cover_letter_upload":

                continue

            if mapped == "full_name":

                fn = profile.first_name or ""

                ln = profile.last_name or ""

                full = (fn + " " + ln).strip()

                if full:

                    try:

                        await self._type_human(loc, full)

                        filled.append("full_name")

                    except Exception as exc:

                        logger.warning("generic_fill_full_name_failed", extra={"error": str(exc)})

                continue

            value: str | None = None

            if mapped == "first_name":

                value = profile.first_name

            elif mapped == "last_name":

                value = profile.last_name

            elif mapped == "email":

                value = profile.linkedin_email

            elif mapped == "phone":

                value = normalize_phone(profile.phone) if profile.phone else None

            elif mapped == "linkedin":

                value = profile.linkedin_url

            elif mapped == "github":

                value = profile.github_url

            elif mapped == "portfolio":

                value = profile.portfolio_url or profile.website_url

            elif mapped in ("city", "state", "country", "zipcode"):

                value = profile.location

            if not value:

                continue

            try:

                tag = await loc.evaluate("e => e.tagName.toLowerCase()")

                if tag == "textarea":

                    await self._type_human(loc, str(value))

                else:

                    await self._type_human(loc, str(value))

                filled.append(mapped)

            except Exception as exc:

                logger.warning("generic_fill_mapped_failed", extra={"mapped": mapped, "error": str(exc)})

        unfilled = self.get_unfilled_required(fields, filled)

        screenshot_path: str | None = None

        try:

            screenshot_path = await self._browser.capture_screenshot(page, screenshot_prefix)

        except Exception as exc:

            logger.warning("generic_screenshot_failed", extra={"error": str(exc)})

        return FillResult(
            filled_fields=filled,
            unfilled_required=unfilled,
            screenshot_path=screenshot_path,
        )

    async def try_submit(self, page: Page) -> bool:

        selectors = (
            'button[type="submit"]',
            'input[type="submit"]',
        )

        for sel in selectors:

            loc = page.locator(sel).first

            try:

                await loc.wait_for(state="visible", timeout=2500)

                await loc.click()

                await page.wait_for_load_state("domcontentloaded", timeout=15000)

                return True

            except Exception:

                continue

        for phrase in ("apply", "submit application", "submit"):
            rx = re.compile(re.escape(phrase), re.I)
            btn = page.get_by_role("button", name=rx).first

            try:

                if await btn.is_visible():

                    await btn.click()

                    await page.wait_for_load_state("domcontentloaded", timeout=15000)

                    return True

            except Exception:

                continue

        return False
