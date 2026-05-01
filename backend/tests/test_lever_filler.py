import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.ats_fillers.lever import LeverFiller
from app.services.ats_fillers.exceptions import ATSSubmitError, FillResult


def _make_mock_page() -> AsyncMock:
    page = AsyncMock()
    page.url = "https://jobs.lever.co/test/abc-123"
    element = AsyncMock()
    page.query_selector.return_value = element
    return page


def _make_mock_browser_service() -> AsyncMock:
    service = AsyncMock()
    service.capture_screenshot.return_value = "/screenshots/test.png"
    return service


def _make_filler() -> LeverFiller:
    return LeverFiller(_make_mock_browser_service())


def _make_profile(**overrides) -> MagicMock:
    profile = MagicMock()
    profile.first_name = "Jane"
    profile.last_name = "Smith"
    profile.linkedin_email = "jane@example.com"
    profile.phone = "+1-555-987-6543"
    profile.location = "New York, NY"
    profile.linkedin_url = "https://linkedin.com/in/jane"
    profile.github_url = "https://github.com/jane"
    profile.portfolio_url = None
    profile.website_url = None
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


class TestCanHandle:
    @pytest.mark.asyncio
    async def test_detects_react_application_form(self):
        filler = _make_filler()
        page = _make_mock_page()

        form_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: form_element if sel == 'div[data-react-class="ApplicationForm"]' else None

        result = await filler.can_handle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_lever_application_form(self):
        filler = _make_filler()
        page = _make_mock_page()

        form_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: form_element if sel == ".lever-application-form" else None

        result = await filler.can_handle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_rejects_unknown_page(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        result = await filler.can_handle(page)
        assert result is False


class TestFill:
    @pytest.mark.asyncio
    async def test_returns_fill_result(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile()

        result = await filler.fill(page, profile)

        assert isinstance(result, FillResult)

    @pytest.mark.asyncio
    async def test_fills_full_name(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile()

        result = await filler.fill(page, profile)

        name_fields = [r for r in result.filled if r.field_name == "name"]
        assert len(name_fields) == 1
        assert name_fields[0].success is True

    @pytest.mark.asyncio
    async def test_fills_url_fields(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile(
            linkedin_url="https://linkedin.com/in/jane",
            github_url="https://github.com/jane",
        )

        result = await filler.fill(page, profile)

        url_fields = [r for r in result.filled if r.field_name in ("linkedin", "github")]
        assert len(url_fields) == 2

    @pytest.mark.asyncio
    async def test_skips_resume_without_path(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile()

        result = await filler.fill(page, profile, resume_path=None)

        resume_skipped = [r for r in result.skipped if r.field_name == "resume"]
        assert len(resume_skipped) >= 1

    @pytest.mark.asyncio
    async def test_skips_missing_urls(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile(
            linkedin_url=None,
            github_url=None,
            portfolio_url=None,
            website_url=None,
        )

        result = await filler.fill(page, profile)

        url_fields = [r for r in result.filled if r.field_name in ("linkedin", "github", "portfolio", "website")]
        assert len(url_fields) == 0


class TestSubmit:
    @pytest.mark.asyncio
    async def test_clicks_submit_button(self):
        filler = _make_filler()
        page = _make_mock_page()

        result = await filler.submit(page)

        assert result is True

    @pytest.mark.asyncio
    async def test_falls_back_to_btn_submit(self):
        filler = _make_filler()
        page = _make_mock_page()

        btn_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: btn_element if sel == ".btn-submit" else None

        result = await filler.submit(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_raises_when_no_submit_button(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        with pytest.raises(ATSSubmitError, match="Submit button not found"):
            await filler.submit(page)


class TestVerify:
    @pytest.mark.asyncio
    async def test_success_with_confirmation_class(self):
        filler = _make_filler()
        page = _make_mock_page()

        confirm_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: confirm_element if sel == ".application-complete" else AsyncMock()

        result = await filler.verify(page)

        assert result.success is True
        assert result.platform == "lever"

    @pytest.mark.asyncio
    async def test_success_with_thanks_url(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.url = "https://jobs.lever.co/test/abc-123/thanks"
        page.query_selector.return_value = None

        result = await filler.verify(page)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_success_with_applied_url(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.url = "https://jobs.lever.co/test/abc-123/applied"
        page.query_selector.return_value = None

        result = await filler.verify(page)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_failure_no_confirmation(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.url = "https://jobs.lever.co/test/abc-123"
        page.query_selector.return_value = None

        result = await filler.verify(page)

        assert result.success is False
        assert result.platform == "lever"


class TestSelectors:
    def test_selectors_is_class_level_dict(self):
        assert isinstance(LeverFiller.SELECTORS, dict)
        assert "name" in LeverFiller.SELECTORS
        assert "email" in LeverFiller.SELECTORS
        assert "submit" in LeverFiller.SELECTORS
