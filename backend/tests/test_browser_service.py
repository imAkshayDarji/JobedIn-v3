import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.browser_service import BrowserService


@pytest.fixture
def mock_playwright_chain():
    """Build the full mock chain: async_playwright -> start -> chromium.launch -> new_context."""
    mock_pw_instance = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()

    mock_pw_instance.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context

    # async_playwright() returns an object whose .start() is a coroutine
    mock_pw_context = MagicMock()
    mock_pw_context.start = AsyncMock(return_value=mock_pw_instance)

    return {
        "pw_context": mock_pw_context,
        "pw_instance": mock_pw_instance,
        "browser": mock_browser,
        "context": mock_context,
    }


@pytest.fixture
def service():
    return BrowserService(headless=True, screenshot_dir="/tmp/test_screenshots")


async def test_aenter_starts_browser(service, mock_playwright_chain):
    with patch("app.services.browser_service.async_playwright", return_value=mock_playwright_chain["pw_context"]), \
         patch("os.makedirs"):
        result = await service.__aenter__()

    assert result is service
    mock_playwright_chain["pw_context"].start.assert_awaited_once()
    mock_playwright_chain["pw_instance"].chromium.launch.assert_awaited_once_with(headless=True)
    mock_playwright_chain["browser"].new_context.assert_awaited_once()
    mock_playwright_chain["context"].add_init_script.assert_awaited_once()


async def test_aexit_closes_resources(service, mock_playwright_chain):
    with patch("app.services.browser_service.async_playwright", return_value=mock_playwright_chain["pw_context"]), \
         patch("os.makedirs"):
        await service.__aenter__()
        await service.__aexit__(None, None, None)

    mock_playwright_chain["context"].close.assert_awaited_once()
    mock_playwright_chain["browser"].close.assert_awaited_once()
    mock_playwright_chain["pw_instance"].stop.assert_awaited_once()

    assert service._context is None
    assert service._browser is None
    assert service._playwright is None


async def test_new_page_raises_without_init(service):
    with pytest.raises(RuntimeError, match="BrowserService is not initialized"):
        await service.new_page()


async def test_new_page_returns_page(service, mock_playwright_chain):
    mock_page = AsyncMock()
    mock_playwright_chain["context"].new_page.return_value = mock_page

    with patch("app.services.browser_service.async_playwright", return_value=mock_playwright_chain["pw_context"]), \
         patch("os.makedirs"):
        await service.__aenter__()
        page = await service.new_page()

    assert page is mock_page
    mock_playwright_chain["context"].new_page.assert_awaited_once()


async def test_safe_goto_success(service):
    mock_page = AsyncMock()
    expected_response = MagicMock()
    mock_page.goto.return_value = expected_response

    result = await service.safe_goto(mock_page, "https://example.com")

    assert result is expected_response
    mock_page.goto.assert_awaited_once_with(
        "https://example.com",
        wait_until="domcontentloaded",
        timeout=30000,
    )


async def test_safe_goto_failure_returns_none(service):
    mock_page = AsyncMock()
    mock_page.goto.side_effect = Exception("Navigation timeout")

    result = await service.safe_goto(mock_page, "https://example.com")

    assert result is None


async def test_wait_for_selector_safe_success(service):
    mock_page = AsyncMock()
    expected_element = MagicMock()
    mock_page.wait_for_selector.return_value = expected_element

    result = await service.wait_for_selector_safe(mock_page, ".job-card", timeout_ms=5000)

    assert result is expected_element
    mock_page.wait_for_selector.assert_awaited_once_with(".job-card", timeout=5000)


async def test_wait_for_selector_safe_failure_returns_none(service):
    mock_page = AsyncMock()
    mock_page.wait_for_selector.side_effect = Exception("Selector not found")

    result = await service.wait_for_selector_safe(mock_page, ".missing")

    assert result is None


async def test_capture_screenshot_creates_file(service):
    mock_page = AsyncMock()

    with patch("os.makedirs"), \
         patch("os.path.getsize", return_value=1024):
        path = await service.capture_screenshot(mock_page, "test_shot")

    assert path == "/tmp/test_screenshots/test_shot.png"
    mock_page.screenshot.assert_awaited_once_with(
        path="/tmp/test_screenshots/test_shot.png",
        full_page=False,
    )


async def test_random_delay_sleeps(service):
    with patch("app.services.browser_service.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await service.random_delay(2.0, 5.0)

    mock_sleep.assert_awaited_once()
    actual_delay = mock_sleep.call_args[0][0]
    assert 2.0 <= actual_delay <= 5.0
