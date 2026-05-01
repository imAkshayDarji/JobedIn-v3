import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.ats_fillers.base_filler import BaseATSFiller, MAX_ENTRIES, normalize_phone
from app.services.ats_fillers.exceptions import ATSFormError, FieldResult


def _make_mock_page() -> AsyncMock:
    page = AsyncMock()
    element = AsyncMock()
    element.is_checked.return_value = False
    page.query_selector.return_value = element
    return page


def _make_mock_browser_service() -> AsyncMock:
    service = AsyncMock()
    service.capture_screenshot.return_value = "/screenshots/test.png"
    return service


def _make_base_filler() -> BaseATSFiller:
    return BaseATSFiller(_make_mock_browser_service())


class TestNormalizePhone:
    def test_us_with_country_code(self):
        assert normalize_phone("+1-555-123-4567") == "5551234567"

    def test_us_with_plus_one(self):
        assert normalize_phone("+15551234567") == "5551234567"

    def test_us_ten_digits(self):
        assert normalize_phone("555-123-4567") == "5551234567"

    def test_us_eleven_digits(self):
        assert normalize_phone("1-555-123-4567") == "5551234567"

    def test_international_with_plus(self):
        assert normalize_phone("+44-20-7946-0958") == "+442079460958"

    def test_empty_string(self):
        assert normalize_phone("") == ""

    def test_none_returns_empty(self):
        assert normalize_phone(None) == ""

    def test_parentheses_format(self):
        assert normalize_phone("(555) 123-4567") == "5551234567"

    def test_spaces_only_digits(self):
        assert normalize_phone("555 123 4567") == "5551234567"


class TestFillTextField:
    @pytest.mark.asyncio
    async def test_success(self):
        base = _make_base_filler()
        page = _make_mock_page()

        result = await base.fill_text_field(page, "#first_name", "first_name", "John")

        assert result.success is True
        assert result.field_name == "first_name"
        assert result.selector == "#first_name"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        base = _make_base_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        result = await base.fill_text_field(page, "#missing", "missing", "value")

        assert result.success is False
        assert result.error == "element_not_found"

    @pytest.mark.asyncio
    async def test_exception_returns_failure(self):
        base = _make_base_filler()
        page = _make_mock_page()
        page.query_selector.side_effect = Exception("DOM error")

        result = await base.fill_text_field(page, "#field", "field", "value")

        assert result.success is False
        assert "DOM error" in result.error


class TestSelectDropdown:
    @pytest.mark.asyncio
    async def test_success(self):
        base = _make_base_filler()
        page = _make_mock_page()

        result = await base.select_dropdown(page, "#country", "country", "United States")

        assert result.success is True
        assert result.field_name == "country"

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        base = _make_base_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        result = await base.select_dropdown(page, "#missing", "missing", "value")

        assert result.success is False
        assert result.error == "element_not_found"


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self):
        base = _make_base_filler()
        page = _make_mock_page()

        with patch("app.services.ats_fillers.base_filler.settings") as mock_settings:
            mock_settings.ATS_RESUME_DIR = "/safe/resumes"
            with pytest.raises(ATSFormError, match="Path traversal"):
                await base.upload_file(page, "#resume", "resume", "/etc/passwd")

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        base = _make_base_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        with patch("app.services.ats_fillers.base_filler.settings") as mock_settings:
            mock_settings.ATS_RESUME_DIR = "/safe/resumes"
            result = await base.upload_file(page, "#resume", "resume", "/safe/resumes/resume.pdf")

        assert result.success is False
        assert result.error == "element_not_found"

    @pytest.mark.asyncio
    async def test_success(self):
        base = _make_base_filler()
        page = _make_mock_page()

        with patch("app.services.ats_fillers.base_filler.settings") as mock_settings:
            mock_settings.ATS_RESUME_DIR = "/safe/resumes"
            result = await base.upload_file(page, "#resume", "resume", "/safe/resumes/resume.pdf")

        assert result.success is True
        assert result.field_name == "resume"


class TestCheckCheckbox:
    @pytest.mark.asyncio
    async def test_success_unchecked(self):
        base = _make_base_filler()
        page = _make_mock_page()
        element = AsyncMock()
        element.is_checked.return_value = False
        page.query_selector.return_value = element

        result = await base.check_checkbox(page, "#agree", "agree")

        assert result.success is True
        element.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_already_checked(self):
        base = _make_base_filler()
        page = _make_mock_page()
        element = AsyncMock()
        element.is_checked.return_value = True
        page.query_selector.return_value = element

        result = await base.check_checkbox(page, "#agree", "agree")

        assert result.success is True
        element.click.assert_not_called()

    @pytest.mark.asyncio
    async def test_element_not_found(self):
        base = _make_base_filler()
        page = _make_mock_page()
        page.query_selector.return_value = None

        result = await base.check_checkbox(page, "#missing", "missing")

        assert result.success is False
        assert result.error == "element_not_found"


class TestFillNameFields:
    @pytest.mark.asyncio
    async def test_both_names_filled(self):
        base = _make_base_filler()
        page = _make_mock_page()
        profile = MagicMock()
        profile.first_name = "John"
        profile.last_name = "Doe"

        results = await base.fill_name_fields(page, profile, "#first", "#last")

        assert len(results) == 2
        assert results[0].field_name == "first_name"
        assert results[0].success is True
        assert results[1].field_name == "last_name"
        assert results[1].success is True

    @pytest.mark.asyncio
    async def test_missing_first_name(self):
        base = _make_base_filler()
        page = _make_mock_page()
        profile = MagicMock()
        profile.first_name = ""
        profile.last_name = "Doe"

        results = await base.fill_name_fields(page, profile, "#first", "#last")

        assert results[0].success is False
        assert results[0].error == "no_value"


class TestFillContactFields:
    @pytest.mark.asyncio
    async def test_all_contact_fields(self):
        base = _make_base_filler()
        page = _make_mock_page()
        profile = MagicMock()
        profile.linkedin_email = "test@example.com"
        profile.phone = "+1-555-123-4567"
        profile.location = "San Francisco, CA"

        results = await base.fill_contact_fields(
            page, profile, "#email", "#phone", "#location",
        )

        assert len(results) == 3
        assert all(r.success for r in results)
        phone_result = [r for r in results if r.field_name == "phone"][0]
        assert phone_result.success is True

    @pytest.mark.asyncio
    async def test_no_values_skipped(self):
        base = _make_base_filler()
        page = _make_mock_page()
        profile = MagicMock()
        profile.linkedin_email = None
        profile.phone = None
        profile.location = None

        results = await base.fill_contact_fields(
            page, profile, "#email", "#phone", "#location",
        )

        assert len(results) == 3
        assert all(r.success is False for r in results)
        assert all(r.error == "no_value" for r in results)


class TestFillEducationFields:
    @pytest.mark.asyncio
    async def test_fills_single_education(self):
        base = _make_base_filler()
        page = _make_mock_page()
        edu = MagicMock()
        edu.institution = "MIT"
        edu.degree = "BS"
        edu.field_of_study = "Computer Science"

        selectors = {
            "institution": "#edu_school_{i}",
            "degree": "#edu_degree_{i}",
            "field_of_study": "#edu_field_{i}",
        }

        results = await base.fill_education_fields(page, [edu], selectors, 0)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_index_out_of_range(self):
        base = _make_base_filler()
        page = _make_mock_page()

        results = await base.fill_education_fields(page, [], {}, 0)

        assert results == []

    @pytest.mark.asyncio
    async def test_max_entries_limit(self):
        base = _make_base_filler()
        page = _make_mock_page()
        edu = MagicMock()
        edu.institution = "MIT"
        edu.degree = "BS"
        edu.field_of_study = "CS"

        selectors = {
            "institution": "#school_{i}",
            "degree": "#degree_{i}",
            "field_of_study": "#field_{i}",
        }

        results = await base.fill_education_fields(page, [edu], selectors, MAX_ENTRIES)
        assert results == []


class TestFillExperienceFields:
    @pytest.mark.asyncio
    async def test_fills_single_experience(self):
        base = _make_base_filler()
        page = _make_mock_page()
        exp = MagicMock()
        exp.company = "Google"
        exp.title = "Engineer"
        exp.description = "Built things"

        selectors = {
            "company": "#exp_company_{i}",
            "title": "#exp_title_{i}",
            "description": "#exp_desc_{i}",
        }

        results = await base.fill_experience_fields(page, [exp], selectors, 0)

        assert len(results) == 3
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_max_entries_limit(self):
        base = _make_base_filler()
        page = _make_mock_page()
        exp = MagicMock()
        exp.company = "Google"
        exp.title = "Engineer"
        exp.description = "Built things"

        results = await base.fill_experience_fields(page, [exp], {}, MAX_ENTRIES)
        assert results == []


class TestMaxEntries:
    def test_max_entries_is_three(self):
        assert MAX_ENTRIES == 3


class TestWaitAndScreenshot:
    @pytest.mark.asyncio
    async def test_returns_screenshot_path(self):
        browser_service = _make_mock_browser_service()
        base = BaseATSFiller(browser_service)
        page = _make_mock_page()

        path = await base.wait_and_screenshot(page, "test_name")

        assert path == "/screenshots/test.png"
        page.wait_for_load_state.assert_called_with("networkidle")
