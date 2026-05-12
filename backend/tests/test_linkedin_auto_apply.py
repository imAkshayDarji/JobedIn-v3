import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.base import ApplicationStatus, JobSource
from app.services.linkedin_auto_apply import LinkedInAutoApply


def _make_job(
    source_url: str = "https://linkedin.com/jobs/view/123456",
    source: JobSource = JobSource.linkedin,
) -> MagicMock:
    job = MagicMock()
    job.source = source
    job.source_url = source_url
    job.apply_url = None
    return job


def _make_profile(
    linkedin_email: str = "test@example.com",
    linkedin_password_encrypted: str = "encrypted_pw",
    first_name: str = "Test",
    last_name: str = "User",
    phone: str = "+1234567890",
) -> MagicMock:
    profile = MagicMock()
    profile.linkedin_email = linkedin_email
    profile.linkedin_password_encrypted = linkedin_password_encrypted
    profile.first_name = first_name
    profile.last_name = last_name
    profile.phone = phone
    return profile


def _make_browser() -> AsyncMock:
    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=AsyncMock())
    browser.close_page = AsyncMock()
    browser.safe_goto = AsyncMock(return_value=MagicMock(status=200))
    browser.capture_screenshot = AsyncMock(return_value="/screenshots/test.png")
    browser.random_delay = AsyncMock()
    return browser


class TestLinkedInAutoApplyCredentials:
    @pytest.mark.asyncio
    async def test_no_credentials_returns_manual(self):
        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile(linkedin_email=None, linkedin_password_encrypted=None)
        job = _make_job()

        result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.manual_required
        assert "No LinkedIn credentials" in result["notes"]

    @pytest.mark.asyncio
    async def test_no_source_url_returns_manual(self):
        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job(source_url="")

        with patch("app.services.linkedin_auto_apply.LinkedInAutoApply._get_credentials", return_value={"email": "t@e.com", "password": "pw"}):
            result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.manual_required
        assert "No LinkedIn URL" in result["notes"]


class TestLinkedInAutoApplyEasyApply:
    @pytest.mark.asyncio
    async def test_easy_apply_success(self):
        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job()

        mock_page = AsyncMock()
        mock_page.url = "https://linkedin.com/jobs/view/123456"
        mock_page.query_selector = AsyncMock(return_value=None)
        browser.new_page = AsyncMock(return_value=mock_page)

        mock_li_instance = AsyncMock()
        mock_li_instance.login = AsyncMock(return_value=True)

        with patch.object(service, "_get_credentials", return_value={"email": "t@e.com", "password": "pw"}), \
             patch.object(service, "_try_easy_apply", new_callable=AsyncMock) as mock_easy:
            mock_easy.return_value = {
                "status": ApplicationStatus.applied,
                "screenshot_path": "/screenshots/li_success.png",
            }

            with patch("app.services.job_sources.linkedin.LinkedInDiscovery") as mock_li_cls:
                mock_li_cls.return_value.__aenter__ = AsyncMock(return_value=mock_li_instance)
                mock_li_cls.return_value.__aexit__ = AsyncMock(return_value=False)

                result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.applied
        assert result["screenshot_path"] == "/screenshots/li_success.png"

    @pytest.mark.asyncio
    async def test_no_apply_button_returns_manual(self):
        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job()

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        mock_page.locator = MagicMock(return_value=AsyncMock(count=AsyncMock(return_value=0)))
        browser.new_page = AsyncMock(return_value=mock_page)

        mock_li_instance = AsyncMock()
        mock_li_instance.login = AsyncMock(return_value=True)

        with patch.object(service, "_get_credentials", return_value={"email": "t@e.com", "password": "pw"}), \
             patch.object(service, "_try_easy_apply", new_callable=AsyncMock, return_value=None), \
             patch.object(service, "_try_external_apply", new_callable=AsyncMock, return_value=None), \
             patch("app.services.job_sources.linkedin.LinkedInDiscovery") as mock_li_cls:
            mock_li_cls.return_value.__aenter__ = AsyncMock(return_value=mock_li_instance)
            mock_li_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.manual_required
        assert "No Easy Apply" in result["notes"]


class TestLinkedInAutoApplyExternal:
    @pytest.mark.asyncio
    async def test_external_apply_redirect(self):
        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job()

        mock_page = AsyncMock()
        mock_page.query_selector = AsyncMock(return_value=None)
        browser.new_page = AsyncMock(return_value=mock_page)

        mock_li_instance = AsyncMock()
        mock_li_instance.login = AsyncMock(return_value=True)

        with patch.object(service, "_get_credentials", return_value={"email": "t@e.com", "password": "pw"}), \
             patch.object(service, "_try_easy_apply", new_callable=AsyncMock, return_value=None), \
             patch.object(service, "_try_external_apply", new_callable=AsyncMock) as mock_ext, \
             patch("app.services.job_sources.linkedin.LinkedInDiscovery") as mock_li_cls:
            mock_li_cls.return_value.__aenter__ = AsyncMock(return_value=mock_li_instance)
            mock_li_cls.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_ext.return_value = {
                "status": ApplicationStatus.applied_with_issues,
                "manual_url": "https://employer.com/apply",
                "notes": "Submitted via LinkedIn external redirect.",
            }

            result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.applied_with_issues
        assert result["manual_url"] == "https://employer.com/apply"


class TestLinkedInAutoApplyAuthFailure:
    @pytest.mark.asyncio
    async def test_auth_failure_returns_manual(self):
        from app.services.job_sources.exceptions import LinkedInAuthError

        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job()

        mock_li_instance = AsyncMock()
        mock_li_instance.login = AsyncMock(side_effect=LinkedInAuthError("Invalid credentials"))

        with patch.object(service, "_get_credentials", return_value={"email": "t@e.com", "password": "pw"}), \
             patch("app.services.job_sources.linkedin.LinkedInDiscovery") as mock_li_cls:
            mock_li_cls.return_value.__aenter__ = AsyncMock(return_value=mock_li_instance)
            mock_li_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.manual_required
        assert "auth failed" in result["notes"]

    @pytest.mark.asyncio
    async def test_captcha_returns_manual(self):
        from app.services.job_sources.exceptions import LinkedInCAPTCHAError

        browser = _make_browser()
        service = LinkedInAutoApply(browser)
        profile = _make_profile()
        job = _make_job()

        mock_li_instance = AsyncMock()
        mock_li_instance.login = AsyncMock(side_effect=LinkedInCAPTCHAError("CAPTCHA detected"))

        with patch.object(service, "_get_credentials", return_value={"email": "t@e.com", "password": "pw"}), \
             patch("app.services.job_sources.linkedin.LinkedInDiscovery") as mock_li_cls:
            mock_li_cls.return_value.__aenter__ = AsyncMock(return_value=mock_li_instance)
            mock_li_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await service.apply(job, profile, "/resumes/test.txt")

        assert result["status"] == ApplicationStatus.manual_required
        assert "CAPTCHA" in result["notes"]


class TestFieldMapping:
    def test_maps_first_name(self):
        service = LinkedInAutoApply(AsyncMock())
        profile = _make_profile()
        assert service._map_field_to_profile("First Name", profile) == "Test"

    def test_maps_last_name(self):
        service = LinkedInAutoApply(AsyncMock())
        profile = _make_profile()
        assert service._map_field_to_profile("Last Name", profile) == "User"

    def test_maps_email(self):
        service = LinkedInAutoApply(AsyncMock())
        profile = _make_profile()
        assert service._map_field_to_profile("Email Address", profile) == "test@example.com"

    def test_maps_phone(self):
        service = LinkedInAutoApply(AsyncMock())
        profile = _make_profile()
        assert service._map_field_to_profile("Phone Number", profile) == "+1234567890"

    def test_unknown_field_returns_empty(self):
        service = LinkedInAutoApply(AsyncMock())
        profile = _make_profile()
        assert service._map_field_to_profile("Favorite Color", profile) == ""
