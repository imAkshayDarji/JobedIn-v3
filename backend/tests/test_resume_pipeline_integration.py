"""Integration tests for the full resume pipeline."""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.ai import (
    ATSResult,
    GapAnalysis,
    JobAnalysis,
    ResumeContent,
    SkillMatch,
    SkillRequirement,
)
from app.services.ai_client import AIClient, AIResult
from app.services.ai_pipeline import AIPipeline


FIXTURES_DIR = "tests/fixtures/golden_outputs"


def _load_fixture(name: str) -> dict:
    with open(f"{FIXTURES_DIR}/{name}") as f:
        return json.load(f)


def _ai_result(content, **kwargs):
    return AIResult(content=content, model_used="glm-4-plus", **kwargs)


def _make_pipeline_with_side_effects(side_effects):
    mock_client = AsyncMock(spec=AIClient)
    mock_client.call.side_effect = side_effects
    return AIPipeline(ai_client=mock_client), mock_client


class TestResumePipelineHappyPath:
    @pytest.mark.asyncio
    async def test_full_pipeline_happy_path(self):
        job_analysis = JobAnalysis(
            required_skills=[SkillRequirement(name="Python", importance="required")],
            responsibilities=["Build APIs"],
            keywords=["Python", "FastAPI"],
        )
        gap = GapAnalysis(
            matches=[SkillMatch(skill="Python", candidate_has=True, match_quality="exact")],
            strengths=["Strong Python"],
            gaps=[],
            match_score=90.0,
            summary="Great fit",
        )
        resume = ResumeContent(
            sections=[],
            target_keywords_covered=["Python"],
            overall_keyword_coverage=85.0,
        )
        ats = ATSResult(
            overall_score=88.0,
            keyword_score=85.0,
            section_score=90.0,
        )

        pipeline, mock_client = _make_pipeline_with_side_effects([
            _ai_result(job_analysis, prompt_tokens=100, completion_tokens=50, total_tokens=150),
            _ai_result(gap, prompt_tokens=200, completion_tokens=80, total_tokens=280),
            _ai_result(resume, prompt_tokens=300, completion_tokens=120, total_tokens=420),
            _ai_result(ats, prompt_tokens=150, completion_tokens=60, total_tokens=210),
        ])

        result = await pipeline._execute_pipeline(
            job_description="Senior Python Developer at TechCorp...",
            candidate_data={"first_name": "Alice", "skills": [{"name": "Python"}]},
            ctx={"user_id": "user-1"},
        )

        assert result["ats_result"]["overall_score"] == 88.0
        assert result["resume"]["overall_keyword_coverage"] == 85.0
        assert result["job_analysis"]["required_skills"][0]["name"] == "Python"
        assert result["gap_analysis"]["match_score"] == 90.0

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 4
        assert usage["total_tokens"] == 1060


class TestResumePipelineATSRetry:
    @pytest.mark.asyncio
    async def test_ats_retry_then_pass(self):
        job_analysis = JobAnalysis(
            required_skills=[SkillRequirement(name="Python", importance="required")],
            responsibilities=["Build APIs"],
            keywords=["Python"],
        )
        gap = GapAnalysis(
            matches=[SkillMatch(skill="Python", candidate_has=True)],
            strengths=[],
            gaps=[],
            match_score=70.0,
            summary="Ok",
        )
        resume_low = ResumeContent(sections=[], target_keywords_covered=["Python"], overall_keyword_coverage=60.0)
        resume_high = ResumeContent(sections=[], target_keywords_covered=["Python"], overall_keyword_coverage=90.0)
        ats_fail = ATSResult(overall_score=60.0, keyword_score=55.0, section_score=65.0)
        ats_pass = ATSResult(overall_score=82.0, keyword_score=80.0, section_score=85.0)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(gap),
            _ai_result(resume_low),
            _ai_result(ats_fail),
            _ai_result(resume_high),
            _ai_result(ats_pass),
        ])

        result = await pipeline._execute_pipeline(
            job_description="Python Developer...",
            candidate_data={"first_name": "Bob"},
            ctx={"user_id": "user-2"},
        )

        assert result["ats_result"]["overall_score"] == 82.0
        assert result["resume"]["overall_keyword_coverage"] == 90.0

    @pytest.mark.asyncio
    async def test_ats_max_retries_returns_last(self):
        job_analysis = JobAnalysis(
            required_skills=[SkillRequirement(name="Python", importance="required")],
            responsibilities=[],
            keywords=[],
        )
        gap = GapAnalysis(
            matches=[],
            strengths=[],
            gaps=[],
            match_score=50.0,
            summary="Weak",
        )
        resume = ResumeContent(sections=[], target_keywords_covered=[], overall_keyword_coverage=40.0)
        ats_low = ATSResult(overall_score=55.0, keyword_score=50.0, section_score=60.0)

        side_effects = [
            _ai_result(job_analysis),
            _ai_result(gap),
        ]
        for _ in range(3):
            side_effects.append(_ai_result(resume))
            side_effects.append(_ai_result(ats_low))

        pipeline, _ = _make_pipeline_with_side_effects(side_effects)

        result = await pipeline._execute_pipeline(
            job_description="test",
            candidate_data={},
            ctx={"user_id": "user-3"},
        )

        assert result["ats_result"]["overall_score"] == 55.0


class TestResumePipelineTokenTracking:
    @pytest.mark.asyncio
    async def test_token_usage_accumulated_across_pipeline(self):
        job_analysis = JobAnalysis(
            required_skills=[SkillRequirement(name="Python", importance="required")],
            responsibilities=[],
            keywords=[],
        )
        gap = GapAnalysis(
            matches=[], strengths=[], gaps=[], match_score=80.0, summary="ok",
        )
        resume = ResumeContent(sections=[], target_keywords_covered=[], overall_keyword_coverage=80.0)
        ats = ATSResult(overall_score=85.0, keyword_score=80.0, section_score=90.0)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis, prompt_tokens=100, completion_tokens=50),
            _ai_result(gap, prompt_tokens=200, completion_tokens=100),
            _ai_result(resume, prompt_tokens=300, completion_tokens=150),
            _ai_result(ats, prompt_tokens=150, completion_tokens=80),
        ])

        await pipeline._execute_pipeline(
            job_description="test",
            candidate_data={},
            ctx={},
        )

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 4
        assert usage["prompt_tokens"] == 750
        assert usage["completion_tokens"] == 380
        assert "glm-4-plus" in usage["models_used"]


class TestResumePipelineFixtureValidation:
    @pytest.mark.asyncio
    async def test_pipeline_with_fixture_data(self):
        job_fixture = _load_fixture("analyze_job.json")
        job_analysis = JobAnalysis.model_validate(job_fixture)

        gap_fixture = _load_fixture("gap_analysis.json")
        gap = GapAnalysis.model_validate(gap_fixture)

        resume_fixture = _load_fixture("generate_resume.json")
        resume = ResumeContent.model_validate(resume_fixture)

        ats_fixture = _load_fixture("validate_ats.json")
        ats = ATSResult.model_validate(ats_fixture)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(gap),
            _ai_result(resume),
            _ai_result(ats),
        ])

        result = await pipeline._execute_pipeline(
            job_description="Python Developer...",
            candidate_data={"first_name": "Test"},
            ctx={},
        )

        assert result["job_analysis"]["experience_level_required"] == "mid"
        assert result["gap_analysis"]["match_score"] == 75.0
        assert result["ats_result"]["overall_score"] == 85.0
