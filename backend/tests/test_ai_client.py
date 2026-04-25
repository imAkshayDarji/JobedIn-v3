import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ai import JobAnalysis, SkillRequirement
from app.services.ai_client import (
    AIClient,
    AIModelResponseError,
    AIPipelineError,
    AIPipelineExhaustedError,
    MODEL_REGISTRY,
    _extract_json_from_text,
    _get_model_for_task,
)


class TestModelRegistry:
    def test_task_routes_to_correct_model(self):
        with patch.dict(
            "app.services.ai_client.MODEL_REGISTRY",
            {
                "glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm"),
                "openai": MagicMock(model="gpt-4o", api_key="k2", base_url="http://oai"),
            },
        ):
            config, key = _get_model_for_task("analyze_job")
            assert key == "glm"

            config, key = _get_model_for_task("generate_resume")
            assert key == "openai"

    def test_unknown_task_defaults_to_glm(self):
        with patch.dict(
            "app.services.ai_client.MODEL_REGISTRY",
            {
                "glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm"),
                "openai": MagicMock(model="gpt-4o", api_key="k2", base_url="http://oai"),
            },
        ):
            config, key = _get_model_for_task("nonexistent_task")
            assert key == "glm"

    def test_no_models_configured_raises(self):
        with patch.dict("app.services.ai_client.MODEL_REGISTRY", {}, clear=True):
            with pytest.raises(AIPipelineError, match="No AI models configured"):
                _get_model_for_task("analyze_job")


class TestExtractJson:
    def test_plain_json(self):
        text = '{"required_skills": []}'
        assert _extract_json_from_text(text) == '{"required_skills": []}'

    def test_json_in_markdown_fence(self):
        text = '```json\n{"required_skills": []}\n```'
        assert _extract_json_from_text(text) == '{"required_skills": []}'

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"required_skills": []}\nDone.'
        assert _extract_json_from_text(text) == '{"required_skills": []}'

    def test_json_array(self):
        text = '[{"name": "Python"}]'
        assert _extract_json_from_text(text) == '[{"name": "Python"}]'


class TestAIClientRetry:
    @pytest.mark.asyncio
    async def test_successful_call(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": [], "experience_level_required": null}'}}]
        }

        with patch("app.services.ai_client._call_openai_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": [], "experience_level_required": null}'

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

        assert isinstance(result, JobAnalysis)
        assert result.required_skills[0].name == "Python"

    @pytest.mark.asyncio
    async def test_auth_error_no_retry(self):
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=AIPipelineError("Authentication failed for glm-4"),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm")},
            ):
                client = AIClient()
                with pytest.raises(AIPipelineExhaustedError):
                    await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                    )

    @pytest.mark.asyncio
    async def test_malformed_response_retry(self):
        good_json = '{"required_skills": [{"name": "Python", "importance": "required"}], "responsibilities": [], "keywords": [], "tone": "professional", "company_values": [], "experience_level_required": null}'

        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=[
                AIModelResponseError("Malformed"),
                good_json,
            ],
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

        assert isinstance(result, JobAnalysis)

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        with patch(
            "app.services.ai_client._call_openai_api",
            new_callable=AsyncMock,
            side_effect=AIPipelineError("Server error from glm-4 (status=500)"),
        ):
            with patch.dict(
                "app.services.ai_client.MODEL_REGISTRY",
                {"glm": MagicMock(model="glm-4", api_key="k1", base_url="http://glm")},
            ):
                client = AIClient()
                with pytest.raises(AIPipelineExhaustedError, match="All retries exhausted"):
                    await client.call(
                        task="analyze_job",
                        messages=[{"role": "user", "content": "test"}],
                    )


class TestSchemaValidation:
    def test_job_analysis_requires_skills(self):
        with pytest.raises(Exception):
            JobAnalysis()

    def test_job_analysis_valid(self):
        ja = JobAnalysis(
            required_skills=[SkillRequirement(name="Python", importance="required")],
            responsibilities=["Build things"],
            keywords=["Python"],
        )
        assert ja.tone == "professional"
        assert len(ja.required_skills) == 1

    def test_gap_analysis_score_bounds(self):
        from app.schemas.ai import GapAnalysis, SkillMatch

        with pytest.raises(Exception):
            GapAnalysis(
                matches=[SkillMatch(skill="Python", candidate_has=True)],
                strengths=[],
                gaps=[],
                match_score=150.0,
                summary="test",
            )
