import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.base import JobSource
from app.services.apply_url_service import (
    ApplyURLService,
    SourceURLResolution,
    _is_ats_url,
    _detect_ats_platform,
    _follow_http_redirects,
    _parse_html_for_apply_link,
)


def _make_job(
    source: JobSource = JobSource.adzuna,
    source_url: str = "https://example.com/job/123",
    apply_url: str | None = None,
    title: str = "AI Engineer",
    company: str = "TestCo",
) -> MagicMock:
    job = MagicMock()
    job.source = source
    job.source_url = source_url
    job.apply_url = apply_url
    job.title = title
    job.company = company
    return job


def _make_browser_service() -> AsyncMock:
    return AsyncMock()


class TestIsAtsUrl:
    def test_greenhouse_url(self):
        assert _is_ats_url("https://boards.greenhouse.io/company/jobs/123") is True

    def test_lever_url(self):
        assert _is_ats_url("https://jobs.lever.co/company/123") is True

    def test_workday_url(self):
        assert _is_ats_url("https://myworkdayjobs.com/company/jobs/123") is True

    def test_non_ats_url(self):
        assert _is_ats_url("https://example.com/careers") is False


class TestDetectAtsPlatform:
    def test_greenhouse(self):
        assert _detect_ats_platform("https://boards.greenhouse.io/test/jobs/1") == "greenhouse"

    def test_lever(self):
        assert _detect_ats_platform("https://jobs.lever.co/test/1") == "lever"

    def test_workday(self):
        assert _detect_ats_platform("https://myworkdayjobs.com/test/1") == "workday"

    def test_unknown(self):
        assert _detect_ats_platform("https://example.com/apply") is None


class TestParseHtmlForApplyLink:
    @pytest.mark.asyncio
    async def test_finds_apply_link(self):
        html = '<html><body><a href="https://jobs.lever.co/test/123">Apply Now</a></body></html>'
        result = await _parse_html_for_apply_link(html, "https://example.com/job")
        assert result == "https://jobs.lever.co/test/123"

    @pytest.mark.asyncio
    async def test_finds_apply_button_text(self):
        html = '<html><body><a href="/careers/apply">Submit Application</a></body></html>'
        result = await _parse_html_for_apply_link(html, "https://example.com/job")
        assert result == "https://example.com/careers/apply"

    @pytest.mark.asyncio
    async def test_no_apply_link(self):
        html = '<html><body><a href="/about">About Us</a></body></html>'
        result = await _parse_html_for_apply_link(html, "https://example.com/job")
        assert result is None

    @pytest.mark.asyncio
    async def test_ignores_mailto(self):
        html = '<html><body><a href="mailto:hr@test.com">Apply</a></body></html>'
        result = await _parse_html_for_apply_link(html, "https://example.com/job")
        assert result is None


class TestFollowHttpRedirects:
    @pytest.mark.asyncio
    async def test_follows_redirect(self):
        with patch("app.services.apply_url_service.httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.url = "https://final.example.com/job/123"

            mock_ctx = AsyncMock()
            mock_ctx.get.return_value = mock_response
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_ctx

            result = await _follow_http_redirects("https://tracker.example.com/redirect")
            assert result == "https://final.example.com/job/123"

    @pytest.mark.asyncio
    async def test_returns_none_on_error(self):
        import httpx

        with patch("app.services.apply_url_service.httpx.AsyncClient") as mock_client:
            mock_ctx = AsyncMock()
            mock_ctx.get.side_effect = httpx.HTTPError("Connection failed")
            mock_ctx.__aenter__ = AsyncMock(return_value=mock_ctx)
            mock_ctx.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_ctx

            result = await _follow_http_redirects("https://example.com/bad")
            assert result is None


class TestApplyURLService:
    @pytest.mark.asyncio
    async def test_adzuna_with_ats_redirect(self):
        """Adzuna redirect resolves to ATS URL directly."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._follow_http_redirects", new_callable=AsyncMock) as mock_follow:
            mock_follow.return_value = "https://boards.greenhouse.io/test/jobs/1"

            job = _make_job(source=JobSource.adzuna, source_url="https://adzuna.com/track/abc")
            result = await service.resolve(job)

            assert result.apply_url == "https://boards.greenhouse.io/test/jobs/1"
            assert result.ats_platform == "greenhouse"
            assert result.method == "http_redirect_ats"

    @pytest.mark.asyncio
    async def test_adzuna_with_listing_page(self):
        """Adzuna redirect goes to listing page, apply link found in HTML."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._follow_http_redirects", new_callable=AsyncMock) as mock_follow, \
             patch("app.services.apply_url_service._fetch_and_parse", new_callable=AsyncMock) as mock_parse:
            mock_follow.return_value = "https://employer.com/jobs/ai-engineer"
            mock_parse.return_value = ("https://employer.com/jobs/ai-engineer", "https://jobs.lever.co/employer/123")

            job = _make_job(source=JobSource.adzuna, source_url="https://adzuna.com/track/abc")
            result = await service.resolve(job)

            assert result.apply_url == "https://jobs.lever.co/employer/123"
            assert result.ats_platform == "lever"
            assert result.method == "html_parse"

    @pytest.mark.asyncio
    async def test_jsearch_direct_ats_url(self):
        """JSearch source_url is already an ATS URL."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        job = _make_job(
            source=JobSource.jsearch,
            source_url="https://boards.greenhouse.io/test/jobs/1",
        )
        result = await service.resolve(job)

        assert result.apply_url == "https://boards.greenhouse.io/test/jobs/1"
        assert result.ats_platform == "greenhouse"
        assert result.method == "direct_ats"

    @pytest.mark.asyncio
    async def test_jsearch_google_interstitial(self):
        """JSearch Google link followed through redirect to find ATS URL."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._follow_http_redirects", new_callable=AsyncMock) as mock_follow, \
             patch("app.services.apply_url_service._fetch_and_parse", new_callable=AsyncMock) as mock_parse:
            mock_follow.return_value = "https://employer.com/jobs/123"
            mock_parse.return_value = ("https://employer.com/jobs/123", "https://jobs.lever.co/emp/456")

            job = _make_job(
                source=JobSource.jsearch,
                source_url="https://www.google.com/search?q=apply+test",
            )
            result = await service.resolve(job)

            assert result.apply_url == "https://jobs.lever.co/emp/456"
            assert result.ats_platform == "lever"

    @pytest.mark.asyncio
    async def test_reed_listing_with_apply_link(self):
        """Reed listing page parsed for apply link."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._fetch_and_parse", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (
                "https://reed.co.uk/jobs/ai-engineer/123",
                "https://employer.com/apply/456",
            )

            job = _make_job(source=JobSource.reed, source_url="https://reed.co.uk/jobs/ai-engineer/123")
            result = await service.resolve(job)

            assert result.apply_url == "https://employer.com/apply/456"
            assert result.method == "html_parse"

    @pytest.mark.asyncio
    async def test_reed_apply_endpoint_fallback(self):
        """Reed /apply/ endpoint redirect fallback."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._fetch_and_parse", new_callable=AsyncMock) as mock_parse, \
             patch("app.services.apply_url_service._follow_http_redirects", new_callable=AsyncMock) as mock_follow:
            mock_parse.return_value = ("https://reed.co.uk/jobs/123", None)
            mock_follow.return_value = "https://employer.com/careers/apply"

            job = _make_job(source=JobSource.reed, source_url="https://reed.co.uk/jobs/ai-engineer/123")
            result = await service.resolve(job)

            assert result.apply_url == "https://employer.com/careers/apply"
            assert result.method == "reed_apply_redirect"

    @pytest.mark.asyncio
    async def test_remotive_listing_with_apply_link(self):
        """Remotive listing page parsed for apply link."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service._fetch_and_parse", new_callable=AsyncMock) as mock_parse:
            mock_parse.return_value = (
                "https://remotive.com/remote-jobs/ai-engineer/789",
                "https://jobs.lever.co/company/456",
            )

            job = _make_job(source=JobSource.remotive, source_url="https://remotive.com/remote-jobs/ai-engineer/789")
            result = await service.resolve(job)

            assert result.apply_url == "https://jobs.lever.co/company/456"
            assert result.ats_platform == "lever"
            assert result.method == "html_parse"

    @pytest.mark.asyncio
    async def test_no_source_url(self):
        """Job with no source_url returns failed resolution."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        job = _make_job(source=JobSource.adzuna, source_url="")
        result = await service.resolve(job)

        assert result.apply_url is None
        assert result.method == "failed"
        assert "No source_url" in result.error

    @pytest.mark.asyncio
    async def test_generic_fallback(self):
        """Unknown source falls back to generic URLResolver."""
        browser = _make_browser_service()
        service = ApplyURLService(browser)

        with patch("app.services.apply_url_service.URLResolver") as mock_resolver_cls:
            mock_resolver = AsyncMock()
            mock_resolver.resolve.return_value = MagicMock(
                apply_url="https://found.example.com/apply",
                method="web_search",
                error=None,
            )
            mock_resolver_cls.return_value = mock_resolver

            job = _make_job(source=JobSource.linkedin, source_url="https://linkedin.com/jobs/view/123")
            result = await service.resolve(job)

            assert result.apply_url == "https://found.example.com/apply"
            assert result.method == "web_search"
