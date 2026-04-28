"""Integration tests for the full API discovery pipeline.

Mocks all 4 adapters, verifies:
- Parallel fetch
- Dedup across sources
- Ingest into DB (mocked)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_discovery import JobDiscoveryService


JSEARCH_JOBS = [
    {
        "external_id": "js-1",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "location": "London",
        "source_url": "https://jsearch.example.com/1",
        "description": "Build things",
        "salary_min": 50000,
        "salary_max": 80000,
        "salary_currency": "USD",
        "job_type": "full_time",
        "remote_policy": "remote",
    },
    {
        "external_id": "js-2",
        "title": "Data Scientist",
        "company": "Beta Inc",
        "location": "Berlin",
        "source_url": "https://jsearch.example.com/2",
    },
]

ADZUNA_JOBS = [
    {
        "external_id": "adz-1",
        "title": "Software Engineer",
        "company": "Acme Corp",
        "location": "London",
        "source_url": "https://adzuna.example.com/1",
        "description": "Another posting for same job",
        "salary_min": 45000,
        "salary_max": 75000,
        "salary_currency": "GBP",
    },
]

REMOTIVE_JOBS = [
    {
        "external_id": "rem-1",
        "title": "DevOps Engineer",
        "company": "Gamma LLC",
        "location": "Remote",
        "source_url": "https://remotive.example.com/1",
        "job_type": "full_time",
        "remote_policy": "remote",
    },
]

REED_JOBS = [
    {
        "external_id": "reed-1",
        "title": "Product Manager",
        "company": "Delta Ltd",
        "location": "Manchester",
        "source_url": "https://reed.example.com/1",
        "salary_min": 55000,
        "salary_max": 85000,
        "salary_currency": "GBP",
    },
]

ALL_ADAPTERS = ["jsearch", "adzuna", "remotive", "reed"]


def _mock_registry(names):
    return {name: MagicMock(return_value=MagicMock(source_name=name)) for name in names}


class TestAPIDiscoveryPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_dedup_and_ingest(self):
        """End-to-end: 4 adapters -> dedup -> ingest -> verify counts."""
        source_data = {
            "jsearch": JSEARCH_JOBS,
            "adzuna": ADZUNA_JOBS,
            "remotive": REMOTIVE_JOBS,
            "reed": REED_JOBS,
        }

        async def fake_fetch(self, adapter, client, keywords, location):
            return source_data.get(adapter.source_name, [])

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        with (
            patch("app.services.job_discovery.ADAPTER_REGISTRY", _mock_registry(ALL_ADAPTERS)),
            patch("app.services.job_discovery.httpx.AsyncClient"),
            patch.object(JobDiscoveryService, "_fetch_from_adapter", fake_fetch),
        ):
            service = JobDiscoveryService(mock_session)
            result = await service.run_api_discovery(
                keywords=["engineer"],
                location="London",
                sources=ALL_ADAPTERS,
            )

        assert result.total_found == 5
        assert result.new_count >= 3
        assert len(result.errors) == 0

    @pytest.mark.asyncio
    async def test_pipeline_with_empty_sources(self):
        mock_session = AsyncMock()
        service = JobDiscoveryService(mock_session)
        result = await service.run_api_discovery(
            keywords=["engineer"],
            sources=["nonexistent"],
        )
        assert result.total_found == 0
        assert "No valid API sources" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_with_no_keywords(self):
        mock_session = AsyncMock()
        service = JobDiscoveryService(mock_session)
        result = await service.run_api_discovery(
            keywords=[],
        )
        assert result.total_found == 0
        assert "No keywords" in result.errors[0]

    @pytest.mark.asyncio
    async def test_pipeline_dedup_across_sources(self):
        """Two sources return same job -> deduped to 1."""
        same_jobs = [
            {
                "external_id": "dup-1",
                "title": "Software Engineer",
                "company": "Same Corp",
                "location": "London",
                "source_url": "https://a.example.com/1",
            },
        ]

        async def fake_fetch(self, adapter, client, keywords, location):
            return same_jobs

        mock_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.commit = AsyncMock()

        with (
            patch("app.services.job_discovery.ADAPTER_REGISTRY", _mock_registry(["jsearch", "adzuna"])),
            patch("app.services.job_discovery.httpx.AsyncClient"),
            patch.object(JobDiscoveryService, "_fetch_from_adapter", fake_fetch),
        ):
            service = JobDiscoveryService(mock_session)
            result = await service.run_api_discovery(
                keywords=["engineer"],
                sources=["jsearch", "adzuna"],
            )

        assert result.total_found == 2
        assert result.new_count == 1

    @pytest.mark.asyncio
    async def test_pipeline_adapter_failure_graceful(self):
        """One adapter fails -> others still succeed."""
        async def fake_fetch(self, adapter, client, keywords, location):
            if adapter.source_name == "jsearch":
                raise Exception("API down")
            return REED_JOBS

        mock_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_execute_result)
        mock_session.commit = AsyncMock()

        with (
            patch("app.services.job_discovery.ADAPTER_REGISTRY", _mock_registry(["jsearch", "reed"])),
            patch("app.services.job_discovery.httpx.AsyncClient"),
            patch.object(JobDiscoveryService, "_fetch_from_adapter", fake_fetch),
        ):
            service = JobDiscoveryService(mock_session)
            result = await service.run_api_discovery(
                keywords=["engineer"],
                sources=["jsearch", "reed"],
            )

        assert result.total_found == 1
        assert result.new_count == 1
        assert len(result.errors) == 1
        assert "jsearch" in result.errors[0]
