import asyncio
import logging
import os
import time
from pathlib import Path

from playwright.async_api import Browser, BrowserContext, Page, Playwright, Response, async_playwright

from app.config import settings

logger = logging.getLogger(__name__)

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
"""


class BrowserService:
    """Async context manager for Playwright browser automation.

    Provides reusable browser lifecycle management, stealth configuration,
    screenshot capture, and safe navigation. Extracted from LinkedInDiscovery
    for use across LinkedIn scraping and ATS form filling.
    """

    def __init__(
        self,
        headless: bool = True,
        timeout_ms: int = 30000,
        screenshot_dir: str | None = None,
    ) -> None:
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._screenshot_dir = screenshot_dir or settings.ATS_SCREENSHOT_DIR
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def __aenter__(self) -> "BrowserService":
        os.makedirs(self._screenshot_dir, exist_ok=True)

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=self._headless)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )
        await self._apply_stealth(self._context)
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._context is not None:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None

        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

    async def new_page(self) -> Page:
        if self._context is None:
            raise RuntimeError("BrowserService is not initialized. Use as async context manager.")
        return await self._context.new_page()

    async def close_page(self, page: Page) -> None:
        try:
            await page.close()
        except Exception:
            pass

    async def safe_goto(
        self,
        page: Page,
        url: str,
        wait_until: str = "domcontentloaded",
    ) -> Response | None:
        try:
            return await page.goto(url, wait_until=wait_until, timeout=self._timeout_ms)
        except Exception as exc:
            logger.warning(f"Navigation failed for {url}: {exc}")
            return None

    async def wait_for_selector_safe(
        self,
        page: Page,
        selector: str,
        timeout_ms: int | None = None,
    ) -> "object | None":
        from playwright.async_api import ElementHandle

        timeout = timeout_ms or self._timeout_ms
        try:
            return await page.wait_for_selector(selector, timeout=timeout)
        except Exception:
            return None

    async def capture_screenshot(self, page: Page, name: str) -> str:
        screenshot_path = os.path.join(self._screenshot_dir, f"{name}.png")
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)

        await page.screenshot(path=screenshot_path, full_page=False)

        size_bytes = os.path.getsize(screenshot_path)
        logger.info(
            "screenshot_captured",
            extra={"path": screenshot_path, "size_bytes": size_bytes},
        )
        return screenshot_path

    async def _apply_stealth(self, context: BrowserContext) -> None:
        await context.add_init_script(STEALTH_SCRIPT)

    async def random_delay(self, min_s: float = 1.0, max_s: float = 3.0) -> None:
        delay = min_s + (max_s - min_s) * (time.monotonic() % 1.0)
        await asyncio.sleep(delay)
