"""Integration tests for the cover letter pipeline."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.ai import (
    CoverLetterContent,
    CoverLetterParagraph,
    JobAnalysis,
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


def _make_job_analysis() -> JobAnalysis:
    return JobAnalysis(
        required_skills=[SkillRequirement(name="Python", importance="required")],
        responsibilities=["Build APIs"],
        keywords=["Python", "FastAPI"],
    )


class TestCoverLetterHappyPath:
    @pytest.mark.asyncio
    async def test_professional_tone(self):
        job_analysis = _make_job_analysis()
        cover_letter = CoverLetterContent(
            paragraphs=[
                CoverLetterParagraph(heading=None, body="I am writing to express my interest."),
                CoverLetterParagraph(heading=None, body="My experience aligns well."),
            ],
            tone_used="professional",
            keywords_addressed=["Python"],
            full_text="I am writing to express my interest.\nMy experience aligns well.",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis, prompt_tokens=100, total_tokens=150),
            _ai_result(cover_letter, prompt_tokens=200, total_tokens=300),
        ])

        result = await pipeline._execute_cover_letter_pipeline(
            job_description="Senior Python Developer...",
            candidate_data={"first_name": "Alice"},
            tone="professional",
            ctx={"user_id": "user-1"},
        )

        assert result["cover_letter"]["tone_used"] == "professional"
        assert "Python" in result["cover_letter"]["keywords_addressed"]
        assert result["job_analysis"]["required_skills"][0]["name"] == "Python"

    @pytest.mark.asyncio
    async def test_casual_tone(self):
        job_analysis = _make_job_analysis()
        cover_letter = CoverLetterContent(
            paragraphs=[
                CoverLetterParagraph(heading=None, body="Hey there!"),
            ],
            tone_used="casual",
            keywords_addressed=[],
            full_text="Hey there!",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(cover_letter),
        ])

        result = await pipeline._execute_cover_letter_pipeline(
            job_description="Startup role...",
            candidate_data={},
            tone="casual",
            ctx={},
        )

        assert result["cover_letter"]["tone_used"] == "casual"

    @pytest.mark.asyncio
    async def test_enthusiastic_tone(self):
        job_analysis = _make_job_analysis()
        cover_letter = CoverLetterContent(
            paragraphs=[
                CoverLetterParagraph(heading=None, body="I am SO excited about this!"),
            ],
            tone_used="enthusiastic",
            keywords_addressed=[],
            full_text="I am SO excited about this!",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(cover_letter),
        ])

        result = await pipeline._execute_cover_letter_pipeline(
            job_description="Dream job...",
            candidate_data={},
            tone="enthusiastic",
            ctx={},
        )

        assert result["cover_letter"]["tone_used"] == "enthusiastic"


class TestCoverLetterTokenTracking:
    @pytest.mark.asyncio
    async def test_token_usage_in_cover_letter_pipeline(self):
        job_analysis = _make_job_analysis()
        cover_letter = CoverLetterContent(
            paragraphs=[CoverLetterParagraph(heading=None, body="text")],
            tone_used="professional",
            keywords_addressed=[],
            full_text="text",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis, prompt_tokens=100, completion_tokens=50, total_tokens=150),
            _ai_result(cover_letter, prompt_tokens=200, completion_tokens=100, total_tokens=300),
        ])

        result = await pipeline._execute_cover_letter_pipeline(
            job_description="test",
            candidate_data={},
            tone="professional",
            ctx={},
        )

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 2
        assert usage["total_tokens"] == 450


class TestCoverLetterFixtureValidation:
    @pytest.mark.asyncio
    async def test_pipeline_with_fixture_data(self):
        job_fixture = _load_fixture("analyze_job.json")
        job_analysis = JobAnalysis.model_validate(job_fixture)

        cl_fixture = _load_fixture("generate_cover_letter.json")
        cover_letter = CoverLetterContent.model_validate(cl_fixture)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(cover_letter),
        ])

        result = await pipeline._execute_cover_letter_pipeline(
            job_description="test",
            candidate_data={},
            tone="professional",
            ctx={},
        )

        assert result["cover_letter"]["tone_used"] == "professional"
        assert len(result["cover_letter"]["paragraphs"]) == 3
