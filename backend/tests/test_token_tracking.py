"""Tests for token tracking: extraction, persistence, and aggregation."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_client import AIClient, AIResult
from app.services.ai_pipeline import AIPipeline
from app.schemas.ai import (
    JobAnalysis,
    GapAnalysis,
    SkillMatch,
    SkillRequirement,
)


def _ai_result(content, **kwargs):
    return AIResult(content=content, model_used="glm-4-plus", **kwargs)


def _make_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        required_skills=[SkillRequirement(name="Python", importance="required")],
        responsibilities=[],
        keywords=[],
    )


class TestTokenExtractionFromResponse:
    @pytest.mark.asyncio
    async def test_usage_fields_populated(self):
        raw_json = '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": []}'

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=(raw_json, {"prompt_tokens": 123, "completion_tokens": 45, "total_tokens": 168}),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm")},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                    response_model=JobAnalysis,
                )

        assert result.prompt_tokens == 123
        assert result.completion_tokens == 45
        assert result.total_tokens == 168

    @pytest.mark.asyncio
    async def test_missing_usage_defaults_to_zero(self):
        raw_json = '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": []}'

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=(raw_json, None),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm")},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                    response_model=JobAnalysis,
                )

        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.total_tokens == 0

    @pytest.mark.asyncio
    async def test_partial_usage_fields(self):
        raw_json = '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": []}'

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=(raw_json, {"prompt_tokens": 100}),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm")},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                    response_model=JobAnalysis,
                )

        assert result.prompt_tokens == 100
        assert result.completion_tokens == 0
        assert result.total_tokens == 0


class TestTokenUsageAggregation:
    @pytest.mark.asyncio
    async def test_aggregation_across_multiple_calls(self):
        mock_client = AsyncMock(spec=AIClient)
        mock_client.call.side_effect = [
            _ai_result(_make_job_analysis(), prompt_tokens=100, completion_tokens=50, total_tokens=150),
            _ai_result(
                GapAnalysis(matches=[], strengths=[], gaps=[], match_score=80.0, summary="ok"),
                prompt_tokens=200, completion_tokens=100, total_tokens=300,
            ),
            _ai_result(_make_job_analysis(), prompt_tokens=50, completion_tokens=25, total_tokens=75),
        ]

        pipeline = AIPipeline(ai_client=mock_client)
        await pipeline.analyze_job("test1")
        await pipeline.gap_analysis(_make_job_analysis(), {})
        await pipeline.analyze_job("test2")

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 3
        assert usage["prompt_tokens"] == 350
        assert usage["completion_tokens"] == 175
        assert usage["total_tokens"] == 525
        assert "glm-4-plus" in usage["models_used"]

    @pytest.mark.asyncio
    async def test_empty_pipeline_usage(self):
        pipeline = AIPipeline(ai_client=AsyncMock(spec=AIClient))
        usage = pipeline.get_token_usage()
        assert usage["calls"] == 0
        assert usage["prompt_tokens"] == 0
        assert usage["models_used"] == []


class TestTokenUsageModelFields:
    def test_ai_result_dataclass_fields(self):
        result = AIResult(
            content="test",
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
            model_used="glm-4-plus",
            latency_ms=1234.5,
        )
        assert result.content == "test"
        assert result.prompt_tokens == 100
        assert result.completion_tokens == 50
        assert result.total_tokens == 150
        assert result.model_used == "glm-4-plus"
        assert result.latency_ms == 1234.5

    def test_ai_result_defaults(self):
        result = AIResult()
        assert result.content == ""
        assert result.prompt_tokens == 0
        assert result.completion_tokens == 0
        assert result.total_tokens == 0
        assert result.model_used == ""
        assert result.latency_ms == 0.0

    def test_ai_result_with_pydantic_content(self):
        ja = _make_job_analysis()
        result = AIResult(content=ja, prompt_tokens=100)
        assert isinstance(result.content, JobAnalysis)
        assert result.content.required_skills[0].name == "Python"
