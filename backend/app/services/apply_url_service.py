"""Unified apply URL resolution with source-specific strategies.

Resolves listing URLs from job aggregators (Adzuna, JSearch, Reed, Remotive)
to direct apply URLs. Each source has a tailored resolution strategy because
their URL structures differ significantly.

Resolution flow:
  1. Check if source_url is already a direct ATS URL (JSearch sometimes is)
  2. Follow HTTP redirects via httpx (fast, no browser)
  3. Parse HTML for apply links (fast, no browser)
  4. Navigate with Playwright and find apply link (slow, browser)
  5. Fall back to generic URLResolver (source navigation + web search)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.config import settings
from app.models.base import JobSource
from app.services.ats_detector import ATS_URL_PATTERNS
from app.services.url_resolver import URLResolution, URLResolver
from app.services.url_validator import validate_apply_url

if TYPE_CHECKING:
    from app.models.job import Job
    from app.services.browser_service import BrowserService

logger = logging.getLogger(__name__)

APPLY_LINK_HREF_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"/apply", re.IGNORECASE),
    re.compile(r"/application", re.IGNORECASE),
    re.compile(r"jobs\.lever\.co/", re.IGNORECASE),
    re.compile(r"boards\.greenhouse\.io/", re.IGNORECASE),
    re.compile(r"myworkdayjobs\.com/", re.IGNORECASE),
]

APPLY_LINK_TEXT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"apply\s*(now)?", re.IGNORECASE),
    re.compile(r"submit\s*application", re.IGNORECASE),
    re.compile(r"start\s*application", re.IGNORECASE),
]

HTTPX_TIMEOUT = httpx.Timeout(timeout=15.0)


def _is_ats_url(url: str) -> bool:
    """Check if a URL matches a known ATS platform pattern."""
    for patterns in ATS_URL_PATTERNS.values():
        for pat in patterns:
            if pat.search(url):
                return True
    return False


def _detect_ats_platform(url: str) -> str | None:
    """Return the ATS platform name if the URL matches a known pattern."""
    for platform, patterns in ATS_URL_PATTERNS.items():
        for pat in patterns:
            if pat.search(url):
                return platform
    return None


@dataclass
class SourceURLResolution:
    apply_url: str | None
    ats_platform: str | None
    method: str
    error: str | None = None


async def _follow_http_redirects(url: str) -> str | None:
    """Follow HTTP redirects via httpx without spawning a browser.

    Returns the final URL after all redirects, or None on failure.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=HTTPX_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as client:
            resp = await client.get(url)
            if resp.status_code < 400:
                ok, _ = validate_apply_url(str(resp.url))
                if ok:
                    return str(resp.url)
    except httpx.HTTPError as exc:
        logger.debug("http_redirect_follow_failed", extra={"url": url, "error": str(exc)})
    return None


def _is_ats_href(href: str) -> bool:
    """Check if the href points to a known ATS platform."""
    ats_hosts = [
        "myworkdayjobs.com",
        "boards.greenhouse.io",
        "jobs.lever.co",
        "icims.com",
        "taleo.net",
        "brassring.com",
        "jobvite.com",
        "smartrecruiters.com",
        "workday.com",
    ]
    href_lower = href.lower()
    return any(host in href_lower for host in ats_hosts)


def _is_false_positive_apply_link(href: str, text: str) -> bool:
    """Filter out common false positive apply links."""
    combined = (href + " " + text).lower()
    false_positive_patterns = [
        "faq",
        "policy",
        "privacy",
        "terms",
        "about",
        "how-to-apply",
        "guide",
        "help",
        "support",
    ]
    # Only flag as false positive if the link itself contains these patterns
    # (not the ATS URL which might coincidentally contain them)
    if _is_ats_href(href):
        return False
    return any(pat in combined for pat in false_positive_patterns)


async def _parse_html_for_apply_link(html: str, base_url: str) -> str | None:
    """Parse HTML for apply links using BeautifulSoup (no browser needed).

    Two-pass strategy:
    1. First pass: look for links whose href points to a known ATS platform
    2. Second pass: look for links matching apply text/href patterns
    This prioritizes real ATS apply URLs over generic "apply" links like FAQ pages.
    """
    soup = BeautifulSoup(html, "html.parser")

    # Pass 1: ATS platform hrefs (highest confidence)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if _is_ats_href(href):
            abs_url = urljoin(base_url, href)
            if abs_url.startswith(("http://", "https://")):
                ok, _ = validate_apply_url(abs_url)
                if ok:
                    return abs_url

    # Pass 2: Apply text/href pattern matches (lower confidence)
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        text = (anchor.get_text() or "").strip().lower()

        if _is_false_positive_apply_link(href, text):
            continue

        href_matches = any(p.search(href) for p in APPLY_LINK_HREF_PATTERNS)
        text_matches = any(p.search(text) for p in APPLY_LINK_TEXT_PATTERNS)

        if href_matches or text_matches:
            abs_url = urljoin(base_url, href)
            if abs_url.startswith(("http://", "https://")):
                ok, _ = validate_apply_url(abs_url)
                if ok:
                    return abs_url

    return None


async def _fetch_and_parse(url: str) -> tuple[str, str | None]:
    """Fetch a URL via httpx and try to find an apply link in the HTML.

    Returns (final_url, apply_link_or_none).
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=HTTPX_TIMEOUT,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        ) as client:
            resp = await client.get(url)
            if resp.status_code >= 400:
                return str(resp.url), None

            final_url = str(resp.url)
            content_type = resp.headers.get("content-type", "")
            if "text/html" not in content_type:
                return final_url, None

            html = resp.text
            apply_link = await _parse_html_for_apply_link(html, final_url)
            return final_url, apply_link
    except httpx.HTTPError as exc:
        logger.debug("fetch_and_parse_failed", extra={"url": url, "error": str(exc)})
        return url, None


class ApplyURLService:
    """Unified URL resolution with source-specific strategies."""

    def __init__(self, browser_service: BrowserService) -> None:
        self._browser = browser_service

    async def resolve(self, job: Job) -> SourceURLResolution:
        """Resolve apply URL using the source-specific strategy."""
        strategy = {
            JobSource.adzuna: self._resolve_adzuna,
            JobSource.jsearch: self._resolve_jsearch,
            JobSource.reed: self._resolve_reed,
            JobSource.remotive: self._resolve_remotive,
        }.get(job.source)

        if strategy:
            return await strategy(job)

        return await self._resolve_generic(job)

    async def _resolve_adzuna(self, job: Job) -> SourceURLResolution:
        """Adzuna: redirect_url → follow redirects → parse listing for apply link.

        The source_url is an Adzuna tracker URL that redirects through Adzuna's
        servers to the employer's job listing. We need to follow the redirect chain
        and then find the apply link on the listing page.
        """
        source_url = (job.source_url or "").strip()
        if not source_url:
            return SourceURLResolution(None, None, "failed", "No source_url for Adzuna job")

        # Step 1: Follow HTTP redirects to get the final listing URL
        final_url = await _follow_http_redirects(source_url)
        if not final_url:
            return await self._fallback_browser(job)

        # Step 2: Check if the final URL is already an ATS apply URL
        if _is_ats_url(final_url):
            return SourceURLResolution(
                apply_url=final_url,
                ats_platform=_detect_ats_platform(final_url),
                method="http_redirect_ats",
            )

        # Step 3: Parse the listing page HTML for an apply link
        _, apply_link = await _fetch_and_parse(final_url)
        if apply_link:
            return SourceURLResolution(
                apply_url=apply_link,
                ats_platform=_detect_ats_platform(apply_link),
                method="html_parse",
            )

        # Step 4: Fall back to browser-based resolution
        return await self._fallback_browser(job)

    async def _resolve_jsearch(self, job: Job) -> SourceURLResolution:
        """JSearch: job_apply_link may already be a direct ATS URL.

        JSearch is unique because it sometimes provides direct ATS URLs.
        Always check first before doing any resolution.
        """
        source_url = (job.source_url or "").strip()
        if not source_url:
            return SourceURLResolution(None, None, "failed", "No source_url for JSearch job")

        # Step 1: Check if already a direct ATS URL
        if _is_ats_url(source_url):
            ok, err = validate_apply_url(source_url)
            if ok:
                return SourceURLResolution(
                    apply_url=source_url,
                    ats_platform=_detect_ats_platform(source_url),
                    method="direct_ats",
                )

        # Step 2: Follow HTTP redirects (handles Google interstitials)
        final_url = await _follow_http_redirects(source_url)
        if final_url and _is_ats_url(final_url):
            return SourceURLResolution(
                apply_url=final_url,
                ats_platform=_detect_ats_platform(final_url),
                method="http_redirect_ats",
            )

        # Step 3: Parse the page for apply links
        check_url = final_url or source_url
        _, apply_link = await _fetch_and_parse(check_url)
        if apply_link:
            return SourceURLResolution(
                apply_url=apply_link,
                ats_platform=_detect_ats_platform(apply_link),
                method="html_parse",
            )

        # Step 4: Fall back to browser-based resolution
        return await self._fallback_browser(job)

    async def _resolve_reed(self, job: Job) -> SourceURLResolution:
        """Reed: listing page has an apply button that redirects to employer site.

        Reed listing URLs (reed.co.uk/jobs/...) contain an apply button that
        redirects through Reed's apply endpoint to the employer's ATS.
        We parse the HTML to find this link.
        """
        source_url = (job.source_url or "").strip()
        if not source_url:
            return SourceURLResolution(None, None, "failed", "No source_url for Reed job")

        # Step 1: Parse Reed listing page for apply link
        _, apply_link = await _fetch_and_parse(source_url)
        if apply_link:
            return SourceURLResolution(
                apply_url=apply_link,
                ats_platform=_detect_ats_platform(apply_link),
                method="html_parse",
            )

        # Step 2: Try the Reed apply URL pattern (/apply/ endpoint)
        if "reed.co.uk" in source_url:
            apply_endpoint = source_url.rstrip("/") + "/apply"
            final_url = await _follow_http_redirects(apply_endpoint)
            if final_url:
                return SourceURLResolution(
                    apply_url=final_url,
                    ats_platform=_detect_ats_platform(final_url),
                    method="reed_apply_redirect",
                )

        # Step 3: Fall back to browser-based resolution
        return await self._fallback_browser(job)

    async def _resolve_remotive(self, job: Job) -> SourceURLResolution:
        """Remotive: listing page has an apply button/link to employer site.

        Remotive listing pages contain an apply link that goes directly to
        the employer's application page.
        """
        source_url = (job.source_url or "").strip()
        if not source_url:
            return SourceURLResolution(None, None, "failed", "No source_url for Remotive job")

        # Step 1: Parse Remotive listing page for apply link
        _, apply_link = await _fetch_and_parse(source_url)
        if apply_link:
            return SourceURLResolution(
                apply_url=apply_link,
                ats_platform=_detect_ats_platform(apply_link),
                method="html_parse",
            )

        # Step 2: Fall back to browser-based resolution
        return await self._fallback_browser(job)

    async def _resolve_generic(self, job: Job) -> SourceURLResolution:
        """Generic fallback: use the existing URLResolver pipeline."""
        resolver = URLResolver(self._browser)
        resolution = await resolver.resolve(job)

        if resolution.apply_url:
            return SourceURLResolution(
                apply_url=resolution.apply_url,
                ats_platform=_detect_ats_platform(resolution.apply_url),
                method=resolution.method,
            )

        return SourceURLResolution(
            apply_url=None,
            ats_platform=None,
            method="failed",
            error=resolution.error,
        )

    async def _fallback_browser(self, job: Job) -> SourceURLResolution:
        """Fall back to browser-based source navigation + web search."""
        return await self._resolve_generic(job)
