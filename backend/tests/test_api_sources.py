"""Unit tests for API source adapters.

7 paths per adapter:
  1. happy path - returns mapped jobs
  2. timeout - raises JobSourceTimeoutError after retries
  3. 401 - raises JobSourceAuthError immediately
  4. 429 - raises JobSourceRateLimitError immediately
  5. 503 - raises JobSourceResponseError after retries
  6. empty response - returns empty list
  7. malformed response - returns empty list (graceful)
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services.job_sources.adzuna import AdzunaAdapter
from app.services.job_sources.exceptions import (
    JobSourceAuthError,
    JobSourceRateLimitError,
    JobSourceResponseError,
    JobSourceTimeoutError,
)
from app.services.job_sources.jsearch import JSearchAdapter
from app.services.job_sources.reed import ReedAdapter
from app.services.job_sources.remotive import RemotiveAdapter


def _make_response(status_code: int, body: dict | None = None) -> httpx.Response:
    return httpx.Response(
        status_code=status_code,
        json=body or {},
        request=httpx.Request("GET", "https://example.com"),
    )


def _make_timeout_response() -> None:
    raise httpx.TimeoutException("timed out")


ADAPTERS = [
    ("jsearch", JSearchAdapter, {"data": [{"job_id": "1", "job_title": "Engineer", "employer_name": "Acme", "job_city": "London"}]}),
    ("adzuna", AdzunaAdapter, {"results": [{"id": 42, "title": "Engineer", "company": {"display_name": "Acme"}, "location": {"display_name": "London"}, "redirect_url": "https://example.com"}]}),
    ("remotive", RemotiveAdapter, {"jobs": [{"id": "99", "title": "Engineer", "company_name": "Acme", "candidate_required_location": "Remote", "url": "https://example.com", "job_type": "full_time"}]}),
    ("reed", ReedAdapter, {"results": [{"jobId": 7, "jobTitle": "Engineer", "employerName": "Acme", "locationName": "London", "jobUrl": "https://example.com"}]}),
]


@pytest.fixture(params=ADAPTERS, ids=[a[0] for a in ADAPTERS])
def adapter_case(request):
    source_name, adapter_cls, happy_body = request.param
    return source_name, adapter_cls(), happy_body


class TestAdapterHappyPath:
    @pytest.mark.asyncio
    async def test_happy_path(self, adapter_case):
        source_name, adapter, happy_body = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(return_value=_make_response(200, happy_body))

        jobs = await adapter.fetch_jobs(client, "engineer", "London")
        assert len(jobs) >= 1
        assert jobs[0]["title"] == "Engineer"
        assert jobs[0]["company"] == "Acme"
        assert "source" not in jobs[0]


class TestAdapterTimeout:
    @pytest.mark.asyncio
    async def test_timeout(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))

        with pytest.raises(JobSourceTimeoutError) as exc_info:
            await adapter.fetch_jobs(client, "engineer", "London")
        assert source_name in str(exc_info.value)


class TestAdapterAuthError:
    @pytest.mark.asyncio
    async def test_401_auth_error(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(return_value=_make_response(401))

        with pytest.raises(JobSourceAuthError) as exc_info:
            await adapter.fetch_jobs(client, "engineer", "London")
        assert source_name in str(exc_info.value)


class TestAdapterRateLimit:
    @pytest.mark.asyncio
    async def test_429_rate_limit(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(return_value=_make_response(429, {"message": "rate limited"}))

        with pytest.raises(JobSourceRateLimitError) as exc_info:
            await adapter.fetch_jobs(client, "engineer", "London")
        assert source_name in str(exc_info.value)


class TestAdapterServerError:
    @pytest.mark.asyncio
    async def test_503_server_error(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(return_value=_make_response(503))

        with pytest.raises(JobSourceResponseError) as exc_info:
            await adapter.fetch_jobs(client, "engineer", "London")
        assert source_name in str(exc_info.value)


class TestAdapterEmptyResponse:
    @pytest.mark.asyncio
    async def test_empty_response(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()

        empty_bodies = {
            "jsearch": {"data": []},
            "adzuna": {"results": []},
            "remotive": {"jobs": []},
            "reed": {"results": []},
        }
        client.get = AsyncMock(return_value=_make_response(200, empty_bodies[source_name]))

        jobs = await adapter.fetch_jobs(client, "engineer", "London")
        assert jobs == []


class TestAdapterMalformedResponse:
    @pytest.mark.asyncio
    async def test_malformed_response(self, adapter_case):
        source_name, adapter, _ = adapter_case
        client = AsyncMock()
        client.get = AsyncMock(return_value=_make_response(200, {"unexpected": "data"}))

        jobs = await adapter.fetch_jobs(client, "engineer", "London")
        assert jobs == []
