import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ats_fillers.greenhouse import GreenhouseFiller
from app.services.ats_fillers.exceptions import ATSSubmitError, FillResult


def _make_mock_page() -> AsyncMock:
    page = AsyncMock()
    page.url = "https://boards.greenhouse.io/test/jobs/1"
    element = AsyncMock()
    element.is_checked.return_value = False
    page.query_selector.return_value = element
    return page


def _make_mock_browser_service() -> AsyncMock:
    service = AsyncMock()
    service.capture_screenshot.return_value = "/screenshots/test.png"
    return service


def _make_filler() -> GreenhouseFiller:
    return GreenhouseFiller(_make_mock_browser_service())


def _make_profile(**overrides) -> MagicMock:
    profile = MagicMock()
    profile.first_name = "John"
    profile.last_name = "Doe"
    profile.linkedin_email = "john@example.com"
    profile.phone = "+1-555-123-4567"
    profile.location = "San Francisco, CA"
    profile.education = []
    profile.experience = []
    for key, value in overrides.items():
        setattr(profile, key, value)
    return profile


class TestCanHandle:
    @pytest.mark.asyncio
    async def test_detects_main_application_form(self):
        filler = _make_filler()
        page = _make_mock_page()

        form_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: form_element if sel == "#main_application_form" else None

        result = await filler.can_handle(page)
        assert result is True

    @pytest.mark.asyncio
    async def test_detects_job_application_input(self):
        filler = _make_filler()
        page = _make_mock_page()

        input_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: input_element if sel == 'input[name="job_application"]' else None

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
        assert isinstance(result.filled, list)
        assert isinstance(result.skipped, list)

    @pytest.mark.asyncio
    async def test_fills_name_fields(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile()

        result = await filler.fill(page, profile)

        name_fields = [r for r in result.filled if r.field_name in ("first_name", "last_name")]
        assert len(name_fields) == 2
        assert all(r.success for r in name_fields)

    @pytest.mark.asyncio
    async def test_skips_resume_without_path(self):
        filler = _make_filler()
        page = _make_mock_page()
        profile = _make_profile()

        result = await filler.fill(page, profile, resume_path=None)

        resume_skipped = [r for r in result.skipped if r.field_name == "resume"]
        assert len(resume_skipped) >= 1
        assert resume_skipped[0].error == "no_resume_path"

    @pytest.mark.asyncio
    async def test_fills_education_entries(self):
        filler = _make_filler()
        page = _make_mock_page()
        edu = MagicMock()
        edu.institution = "MIT"
        edu.degree = "BS"
        edu.field_of_study = "CS"
        profile = _make_profile(education=[edu])

        result = await filler.fill(page, profile)

        edu_fields = [r for r in result.filled if "education" in r.field_name]
        assert len(edu_fields) >= 1

    @pytest.mark.asyncio
    async def test_fills_experience_entries(self):
        filler = _make_filler()
        page = _make_mock_page()
        exp = MagicMock()
        exp.company = "Google"
        exp.title = "Engineer"
        exp.description = "Built things"
        profile = _make_profile(experience=[exp])

        result = await filler.fill(page, profile)

        exp_fields = [r for r in result.filled if "experience" in r.field_name]
        assert len(exp_fields) >= 1

    @pytest.mark.asyncio
    async def test_respects_max_entries(self):
        filler = _make_filler()
        page = _make_mock_page()
        experiences = [MagicMock(company=f"Co{i}", title=f"Title{i}", description=f"Desc{i}") for i in range(5)]
        profile = _make_profile(experience=experiences)

        result = await filler.fill(page, profile)

        exp_fields = [r for r in result.filled if "experience" in r.field_name]
        assert len(exp_fields) <= 9  # 3 entries * 3 fields max


class TestSubmit:
    @pytest.mark.asyncio
    async def test_clicks_submit_button(self):
        filler = _make_filler()
        page = _make_mock_page()

        result = await filler.submit(page)

        assert result is True
        page.query_selector.assert_any_call("#submit_app")

    @pytest.mark.asyncio
    async def test_falls_back_to_submit_type(self):
        filler = _make_filler()
        page = _make_mock_page()

        submit_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: submit_element if sel == "button[type='submit']" else None

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
    async def test_success_with_confirmation_text(self):
        filler = _make_filler()
        page = _make_mock_page()

        confirm_element = AsyncMock()
        page.query_selector.side_effect = lambda sel: confirm_element if sel == "text='You have successfully applied'" else AsyncMock()

        result = await filler.verify(page)

        assert result.success is True
        assert result.platform == "greenhouse"

    @pytest.mark.asyncio
    async def test_success_with_confirmation_url(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.url = "https://boards.greenhouse.io/test/jobs/1/confirmation"
        page.query_selector.return_value = None

        result = await filler.verify(page)

        assert result.success is True
        assert result.platform == "greenhouse"

    @pytest.mark.asyncio
    async def test_failure_no_confirmation(self):
        filler = _make_filler()
        page = _make_mock_page()
        page.url = "https://boards.greenhouse.io/test/jobs/1"
        page.query_selector.return_value = None

        result = await filler.verify(page)

        assert result.success is False
        assert result.platform == "greenhouse"


class TestSelectors:
    def test_selectors_is_class_level_dict(self):
        assert isinstance(GreenhouseFiller.SELECTORS, dict)
        assert "first_name" in GreenhouseFiller.SELECTORS
        assert "submit" in GreenhouseFiller.SELECTORS
        assert "resume" in GreenhouseFiller.SELECTORS
