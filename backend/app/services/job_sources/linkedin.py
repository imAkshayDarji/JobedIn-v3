import asyncio
import logging
import re
from urllib.parse import urlencode

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright

from app.config import settings
from app.services.job_sources.exceptions import (
    LinkedInAuthError,
    LinkedInCAPTCHAError,
    LinkedInScrapeError,
    LinkedInTimeoutError,
)

logger = logging.getLogger(__name__)

LOGIN_URL = "https://www.linkedin.com/login"
JOBS_BASE_URL = "https://www.linkedin.com/jobs/search/"

CAPTCHA_SELECTORS = [
    "div.captcha",
    "#captcha",
    "iframe[src*='captcha']",
    "div[data-testid='captcha']",
    ".challenge-form",
]

LOGIN_TIMEOUT_MS = 30000
PAGE_LOAD_TIMEOUT_MS = 30000


class LinkedInDiscovery:
    def __init__(self, headless: bool = True) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None

    async def __aenter__(self) -> "LinkedInDiscovery":
        await self._start()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def _start(self) -> None:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        await self._apply_stealth()
        self._page = await self._context.new_page()

    async def _apply_stealth(self) -> None:
        if self._context is None:
            return
        await self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
            window.chrome = { runtime: {} };
        """)

    async def login(self, email: str, password: str) -> bool:
        if self._page is None:
            raise LinkedInScrapeError("Browser not initialized. Use async context manager.")

        try:
            await self._page.goto(LOGIN_URL, timeout=PAGE_LOAD_TIMEOUT_MS)
        except Exception as exc:
            raise LinkedInTimeoutError(f"Login page load timed out: {exc}") from exc

        await self._random_delay()

        if await self._detect_captcha():
            raise LinkedInCAPTCHAError("CAPTCHA detected on login page")

        try:
            await self._page.fill('input[id="username"]', email, timeout=5000)
            await self._page.fill('input[id="password"]', password, timeout=5000)
            await self._random_delay()
            await self._page.click('button[type="submit"]', timeout=5000)
        except Exception as exc:
            raise LinkedInAuthError(f"Failed to fill login form: {exc}") from exc

        try:
            await self._page.wait_for_url(
                "**/feed/**",
                timeout=LOGIN_TIMEOUT_MS,
            )
        except Exception:
            pass

        if await self._detect_captcha():
            raise LinkedInCAPTCHAError("CAPTCHA detected after login attempt")

        current_url = self._page.url
        if "login" in current_url or "checkpoint" in current_url:
            raise LinkedInAuthError(
                "Login failed: still on login/checkpoint page after submission"
            )

        return True

    async def search_jobs(
        self,
        keywords: str,
        location: str | None = None,
        experience_level: str | None = None,
        date_filter: str = "past-week",
        max_results: int | None = None,
    ) -> list[dict]:
        if self._page is None:
            raise LinkedInScrapeError("Browser not initialized. Use async context manager.")

        limit = max_results or settings.LINKEDIN_SEARCH_MAX_RESULTS

        params: dict[str, str] = {"keywords": keywords}
        if location:
            params["location"] = location
        if date_filter:
            params["f_TPR"] = date_filter
        if experience_level:
            level_map = {
                "internship": "1",
                "entry": "2",
                "associate": "3",
                "mid-senior": "4",
                "director": "5",
                "executive": "6",
            }
            code = level_map.get(experience_level)
            if code:
                params["f_E"] = code

        url = f"{JOBS_BASE_URL}?{urlencode(params)}"

        try:
            await self._page.goto(url, timeout=PAGE_LOAD_TIMEOUT_MS)
        except Exception as exc:
            raise LinkedInTimeoutError(f"Jobs page load timed out: {exc}") from exc

        await self._random_delay()

        if await self._detect_captcha():
            raise LinkedInCAPTCHAError("CAPTCHA detected during job search")

        return await self._extract_job_cards(limit)

    async def _detect_captcha(self) -> bool:
        if self._page is None:
            return False
        for selector in CAPTCHA_SELECTORS:
            element = await self._page.query_selector(selector)
            if element is not None:
                return True
        return False

    async def _random_delay(self) -> None:
        import random

        delay = random.uniform(
            settings.LINKEDIN_DELAY_MIN_SECONDS,
            settings.LINKEDIN_DELAY_MAX_SECONDS,
        )
        await asyncio.sleep(delay)

    async def _extract_job_cards(self, max_results: int) -> list[dict]:
        if self._page is None:
            return []

        jobs: list[dict] = []
        seen_ids: set[str] = set()

        card_selectors = [
            "div.job-search-card",
            "li.jobs-search__results-list > div",
            "div.base-search-card",
            "div.job-card-container",
        ]

        cards: list[object] = []
        for selector in card_selectors:
            found = await self._page.query_selector_all(selector)
            if found:
                cards = found
                break

        if not cards:
            logger.info("No job cards found with any selector")
            return []

        for card in cards:
            if len(jobs) >= max_results:
                break

            try:
                link_el = await card.query_selector("a.base-card__full-link, a[href*='/jobs/view/']")
                title_el = await card.query_selector("h3.base-search-card__title, h3")
                company_el = await card.query_selector("h4.base-search-card__subtitle, h4 a")
                location_el = await card.query_selector("span.job-search-card__location, span")

                if not link_el or not title_el:
                    continue

                href = await link_el.get_attribute("href") or ""
                title = (await title_el.inner_text()).strip()
                company = (await company_el.inner_text()).strip() if company_el else ""
                location = (await location_el.inner_text()).strip() if location_el else ""

                job_id = self._parse_job_id_from_url(href)
                if not job_id or job_id in seen_ids:
                    continue

                seen_ids.add(job_id)

                jobs.append({
                    "title": title,
                    "company": company,
                    "location": location,
                    "source_url": href,
                    "external_id": job_id,
                    "source": "linkedin",
                })

            except Exception as exc:
                logger.warning(f"Failed to extract job card: {exc}")
                continue

        return jobs

    @staticmethod
    def _parse_job_id_from_url(url: str) -> str | None:
        view_match = re.search(r"/jobs/view/(\d+)", url)
        if view_match:
            return view_match.group(1)

        current_match = re.search(r"currentJobId=(\d+)", url)
        if current_match:
            return current_match.group(1)

        return None

    async def close(self) -> None:
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
