"""3-tier pipeline: apply_url → source_url navigation → web search."""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import quote_plus, urljoin, urlparse

from app.services.ats_detector import ATS_URL_PATTERNS
from app.services.url_validator import validate_apply_url

if TYPE_CHECKING:
    from playwright.async_api import Locator, Page

    from app.models.job import Job
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)

TOTAL_WEB_SEARCH_BUDGET_S = 30.0


@dataclass
class URLResolution:
    apply_url: str | None
    method: str  # "direct" | "source_navigation" | "web_search" | "failed"
    error: str | None = None


def _looks_like_auth_entry_url(url: str) -> bool:
    lower = url.lower()
    if "/login" in lower or "signin" in lower or "/checkpoint/" in lower:
        return True
    return False


async def _visible_inner_text(loc: Locator, max_chars: int = 80) -> str:
    try:
        txt = await loc.inner_text(timeout=2000)
    except Exception:
        return ""
    return (txt or "").strip().lower()[:max_chars]


def _href_matches_apply_pattern(href: str) -> bool:
    hl = href.lower()
    if "/apply" in hl or "/application" in hl:
        return True
    for patterns in ATS_URL_PATTERNS.values():
        for pat in patterns:
            if pat.search(href):
                return True
    return False


async def _text_matches_apply_pattern(text: str) -> bool:
    t = text.lower().strip()
    if not t:
        return False
    for phrase in ("apply now", "apply for", "easy apply", "submit application"):
        if phrase in t:
            return True
    if t in {"apply", "submit", "submit application"}:
        return True
    return False


async def _find_apply_link_on_page(browser: BrowserService, page: Page) -> str | None:
    """Find an apply anchor or submit-style link on the current page."""

    anchors = page.locator("a[href]")
    count = await anchors.count()

    candidates: list[tuple[str, str]] = []

    for i in range(min(count, 200)):
        anchor = anchors.nth(i)
        try:
            if not await anchor.is_visible(timeout=400):
                continue
        except Exception:
            continue
        href_attr = await anchor.get_attribute("href")
        text = await _visible_inner_text(anchor)
        if href_attr and (_href_matches_apply_pattern(href_attr) or await _text_matches_apply_pattern(text)):
            abs_url = urljoin(page.url, href_attr.strip())
            if abs_url.startswith("mailto:"):
                continue
            ok, _ = validate_apply_url(abs_url)
            if ok:
                candidates.append((abs_url, text))

    buttons = page.locator(
        "button, [role=\"button\"], input[type=\"submit\"], input[type=\"button\"]",
    )
    btn_count = await buttons.count()

    for i in range(min(btn_count, 100)):
        btn = buttons.nth(i)
        try:
            if not await btn.is_visible(timeout=400):
                continue
        except Exception:
            continue
        text = await _visible_inner_text(btn)
        if not await _text_matches_apply_pattern(text):
            continue

        try:
            nested = btn.locator("xpath=ancestor::a[@href]")
            if await nested.count() > 0:
                ah = await nested.first.get_attribute("href")
                if ah:
                    abs_url = urljoin(page.url, ah.strip())
                    ok, _ = validate_apply_url(abs_url)
                    if ok:
                        candidates.append((abs_url, text))
        except Exception:
            continue

    for url, _ in candidates:
        if url and url.startswith(("http://", "https://")):
            ok, _ = validate_apply_url(url)
            if ok:
                return url

    return None


class URLResolver:
    """Resolve a workable application URL from job metadata."""

    def __init__(self, browser_service: BrowserService) -> None:
        self._browser = browser_service

    async def resolve(self, job: Job) -> URLResolution:
        """Run the URL resolution tiers in priority order."""

        if job.apply_url:
            candidate = job.apply_url.strip()
            ok, err = validate_apply_url(candidate)
            if ok:
                return URLResolution(apply_url=candidate, method="direct", error=None)
            return URLResolution(apply_url=None, method="failed", error=err)

        resolved: str | None = None
        err: str | None = None

        if job.source_url and not _looks_like_auth_entry_url(job.source_url):
            try:
                resolved = await asyncio.wait_for(
                    self._try_source_url(job.source_url),
                    timeout=TOTAL_WEB_SEARCH_BUDGET_S,
                )
            except TimeoutError:
                err = "source_url navigation timed out"
                logger.warning("url_resolve_source_timeout", extra={"source_url": job.source_url})
            except Exception as exc:
                err = str(exc)
                logger.warning("url_resolve_source_failed", extra={"error": str(exc)})

            if resolved:
                return URLResolution(apply_url=resolved, method="source_navigation", error=None)

        if job.company and job.title:
            search_deadline = time.monotonic() + TOTAL_WEB_SEARCH_BUDGET_S
            try:
                resolved = await self._try_web_search(job.company, job.title, deadline_s=search_deadline)
            except Exception as exc:
                err = str(exc)
                logger.warning("url_resolve_search_failed", extra={"error": str(exc)})

            if resolved:
                return URLResolution(apply_url=resolved, method="web_search", error=None)

        return URLResolution(
            apply_url=None,
            method="failed",
            error=err or "Could not resolve an apply URL from source or web search.",
        )

    async def _try_source_url(self, source_url: str) -> str | None:
        page = await self._browser.new_page()
        try:
            resp = await self._browser.safe_goto(page, source_url)
            if resp is None:
                return None
            if _looks_like_auth_entry_url(page.url):
                logger.info("url_resolve_skip_login_wall", extra={"url": page.url})
                return None
            if "linkedin.com" in page.url.lower() and "/feed" not in page.url.lower():
                title = (await page.title() or "").lower()
                if "sign in" in title or "join linkedin" in title:
                    logger.info("url_resolve_linkedin_auth_wall", extra={"url": page.url})
                    return None

            await self._browser.random_delay(0.4, 1.2)

            found = await _find_apply_link_on_page(self._browser, page)
            return found
        finally:
            await self._browser.close_page(page)

    async def _try_web_search(self, company: str, title: str, deadline_s: float) -> str | None:
        query = f'"{company}" "{title}" apply careers'
        search_url = f"https://www.google.com/search?q={quote_plus(query)}"

        page = await self._browser.new_page()
        try:
            if time.monotonic() > deadline_s:
                return None

            resp = await self._browser.safe_goto(page, search_url)
            if resp is None:
                return None

            await self._browser.random_delay(0.5, 1.0)

            links = page.locator("div#search a[href^=\"http\"]")
            organic: list[str] = []
            n = await links.count()

            for i in range(min(n, 30)):
                if time.monotonic() > deadline_s:
                    break
                href = await links.nth(i).get_attribute("href")
                if not href:
                    continue
                hp = urlparse(href)
                host = hp.netloc.lower()
                if host.endswith("google.com") or host.startswith("accounts."):
                    continue
                organic.append(href)

            uniq: list[str] = []
            for u in organic:
                if u not in uniq:
                    uniq.append(u)
                if len(uniq) >= 5:
                    break

            attempts = 0
            for url in uniq:
                if attempts >= 3:
                    break
                if time.monotonic() > deadline_s:
                    break

                attempts += 1

                landing = await self._browser.new_page()
                try:
                    r = await self._browser.safe_goto(landing, url)
                    if r is None:
                        continue
                    await self._browser.random_delay(0.3, 0.8)

                    page_title = (await landing.title() or "").lower()
                    job_title_lower = title.lower()
                    if job_title_lower and job_title_lower[:24] in page_title:
                        pass

                    found = await _find_apply_link_on_page(self._browser, landing)
                    if found:
                        return found
                finally:
                    await self._browser.close_page(landing)

            return None
        finally:
            await self._browser.close_page(page)
