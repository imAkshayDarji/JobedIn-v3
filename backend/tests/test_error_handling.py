"""Tests for error handling, model fallback, and edge cases."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.ai_client import (
    AIClient,
    AIModelResponseError,
    AIModelTimeoutError,
    AIPipelineError,
    AIPipelineExhaustedError,
    AIResult,
)
from app.services.ai_pipeline import AIPipeline


def _ai_result(content="", **kwargs):
    return AIResult(content=content, model_used="glm-4-plus", **kwargs)


def _mock_config(model="glm-4", api_key="k1", base_url="http://glm"):
    return MagicMock(model=model, api_key=api_key, base_url=base_url)


class TestModelTimeout:
    @pytest.mark.asyncio
    async def test_timeout_raises_error(self):
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=AIModelTimeoutError("Model glm-4 timed out"),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                client = AIClient()
                with pytest.raises(AIPipelineExhaustedError, match="All retries exhausted"):
                    await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                    )


class TestRateLimit:
    @pytest.mark.asyncio
    async def test_500_server_error_retries(self):
        call_count = 0

        async def mock_api(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                raise AIPipelineError("Server error from glm-4 (status=500)")
            return ("text response", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=mock_api,
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                )

        assert isinstance(result, AIResult)
        assert call_count == 2


class TestInvalidOutput:
    @pytest.mark.asyncio
    async def test_non_json_then_correction(self):
        call_count = 0

        async def mock_api(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise AIModelResponseError("Failed to parse JSON")
            return ('{"required_skills": [], "responsibilities": [], "keywords": []}', {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=mock_api,
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                from app.schemas.ai import JobAnalysis
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                    response_model=JobAnalysis,
                )

        assert isinstance(result, AIResult)
        assert isinstance(result.content, JobAnalysis)


class TestGLMToFallback:
    @pytest.mark.asyncio
    async def test_glm_fails_openai_succeeds(self):
        call_count = 0

        async def mock_api(config, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if config.model == "glm-4":
                raise AIPipelineError("Server error from glm-4 (status=500)")
            return ("text response", {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=mock_api,
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {
                    "glm": _mock_config(model="glm-4"),
                    "openai": _mock_config(model="gpt-4o", api_key="k2", base_url="http://oai"),
                },
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                )

        assert isinstance(result, AIResult)
        assert result.content == "text response"


class TestGPT4oToFallback:
    @pytest.mark.asyncio
    async def test_openai_fails_glm_succeeds(self):
        async def mock_api(config, *args, **kwargs):
            if config.model == "gpt-4o":
                raise AIPipelineError("Server error from gpt-4o (status=500)")
            return ("text response", None)

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=mock_api,
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {
                    "glm": _mock_config(model="glm-4"),
                    "openai": _mock_config(model="gpt-4o", api_key="k2", base_url="http://oai"),
                },
            ):
                from app.services.ai_client import TASK_TO_MODEL
                with patch.dict(TASK_TO_MODEL, {"analyze_job": "openai"}):
                    client = AIClient()
                    result = await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                    )

        assert isinstance(result, AIResult)
        assert result.content == "text response"


class TestAllModelsExhausted:
    @pytest.mark.asyncio
    async def test_both_models_500_raises_exhausted(self):
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=AIPipelineError("Server error (status=500)"),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {
                    "glm": _mock_config(model="glm-4"),
                    "openai": _mock_config(model="gpt-4o", api_key="k2", base_url="http://oai"),
                },
            ):
                client = AIClient()
                with pytest.raises(AIPipelineExhaustedError, match="All retries exhausted"):
                    await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                    )


class TestEmptyResponse:
    @pytest.mark.asyncio
    async def test_empty_string_response(self):
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=("", None),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                )

        assert isinstance(result, AIResult)
        assert result.content == ""


class TestModelRefusal:
    @pytest.mark.asyncio
    async def test_refusal_returns_as_content(self):
        refusal_text = "I cannot help with that request."
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=(refusal_text, None),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                client = AIClient()
                result = await client.call(
                    task="analyze_job",
                    messages=[{"role": "user", "content": "test"}],
                )

        assert isinstance(result, AIResult)
        assert result.content == refusal_text

    @pytest.mark.asyncio
    async def test_refusal_with_schema_raises_validation_error(self):
        refusal_text = "I cannot help with that request."
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            return_value=(refusal_text, None),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": _mock_config()},
            ):
                from app.schemas.ai import JobAnalysis
                client = AIClient()
                with pytest.raises(AIPipelineExhaustedError):
                    await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                        response_model=JobAnalysis,
                    )
