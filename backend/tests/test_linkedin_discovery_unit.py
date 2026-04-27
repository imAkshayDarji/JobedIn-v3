from app.services.job_sources.exceptions import (
    LinkedInAuthError,
    LinkedInCAPTCHAError,
    LinkedInDiscoveryError,
    LinkedInScrapeError,
    LinkedInSessionCooldownError,
    LinkedInTimeoutError,
)
from app.services.job_sources.linkedin import LinkedInDiscovery


class TestExceptionHierarchy:
    def test_auth_error_is_discovery_error(self) -> None:
        assert issubclass(LinkedInAuthError, LinkedInDiscoveryError)

    def test_captcha_error_is_discovery_error(self) -> None:
        assert issubclass(LinkedInCAPTCHAError, LinkedInDiscoveryError)

    def test_scrape_error_is_discovery_error(self) -> None:
        assert issubclass(LinkedInScrapeError, LinkedInDiscoveryError)

    def test_timeout_error_is_discovery_error(self) -> None:
        assert issubclass(LinkedInTimeoutError, LinkedInDiscoveryError)

    def test_cooldown_error_is_discovery_error(self) -> None:
        assert issubclass(LinkedInSessionCooldownError, LinkedInDiscoveryError)

    def test_cooldown_error_stores_remaining_hours(self) -> None:
        exc = LinkedInSessionCooldownError(remaining_hours=12.5)
        assert exc.remaining_hours == 12.5
        assert "12.5 hours" in str(exc)

    def test_discovery_error_is_exception(self) -> None:
        assert issubclass(LinkedInDiscoveryError, Exception)


class TestParseJobIdFromUrl:
    def test_view_url(self) -> None:
        url = "https://www.linkedin.com/jobs/view/4012345678"
        assert LinkedInDiscovery._parse_job_id_from_url(url) == "4012345678"

    def test_current_job_id_param(self) -> None:
        url = "https://www.linkedin.com/jobs/search/?currentJobId=3987654321"
        assert LinkedInDiscovery._parse_job_id_from_url(url) == "3987654321"

    def test_view_url_with_trailing_path(self) -> None:
        url = "https://www.linkedin.com/jobs/view/4012345678/?refId=abc"
        assert LinkedInDiscovery._parse_job_id_from_url(url) == "4012345678"

    def test_no_job_id_returns_none(self) -> None:
        url = "https://www.linkedin.com/jobs/search/?keywords=python"
        assert LinkedInDiscovery._parse_job_id_from_url(url) is None

    def test_empty_url_returns_none(self) -> None:
        assert LinkedInDiscovery._parse_job_id_from_url("") is None

    def test_non_numeric_id_from_view(self) -> None:
        url = "https://www.linkedin.com/jobs/view/abc"
        assert LinkedInDiscovery._parse_job_id_from_url(url) is None

    def test_url_with_multiple_params(self) -> None:
        url = (
            "https://www.linkedin.com/jobs/search/?keywords=python"
            "&currentJobId=1234567890&location=London"
        )
        assert LinkedInDiscovery._parse_job_id_from_url(url) == "1234567890"
