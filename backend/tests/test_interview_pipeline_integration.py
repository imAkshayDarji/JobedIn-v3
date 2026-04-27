"""Integration tests for the interview prep + chat pipeline."""
import json
from unittest.mock import AsyncMock, patch

import pytest

from app.schemas.ai import (
    CoachEvaluation,
    InterviewPrepResult,
    InterviewQuestion,
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
        keywords=["Python"],
    )


def _make_questions(count: int = 12) -> InterviewPrepResult:
    questions = []
    categories = ["company_research", "technical", "behavioral", "culture_fit"]
    for i in range(count):
        questions.append(InterviewQuestion(
            question=f"Question {i + 1}",
            category=categories[i % 4],
            difficulty=(i % 3) + 1,
            follow_up_hints=["hint"],
        ))
    return InterviewPrepResult(questions=questions, total_questions=count)


class TestInterviewPrepGeneration:
    @pytest.mark.asyncio
    async def test_prep_generates_12_questions(self):
        job_analysis = _make_job_analysis()
        prep = _make_questions(12)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(prep),
        ])

        result = await pipeline._execute_interview_prep_pipeline(
            job_description="Senior Python Developer...",
            candidate_data={"first_name": "Alice"},
            ctx={"user_id": "user-1"},
        )

        assert result["total_questions"] == 12
        assert len(result["questions"]) == 12

        categories = {q["category"] for q in result["questions"]}
        assert categories == {"company_research", "technical", "behavioral", "culture_fit"}

        difficulties = {q["difficulty"] for q in result["questions"]}
        assert difficulties == {1, 2, 3}

    @pytest.mark.asyncio
    async def test_prep_token_tracking(self):
        job_analysis = _make_job_analysis()
        prep = _make_questions(12)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis, prompt_tokens=100, total_tokens=150),
            _ai_result(prep, prompt_tokens=500, total_tokens=700),
        ])

        await pipeline._execute_interview_prep_pipeline(
            job_description="test",
            candidate_data={},
            ctx={},
        )

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 2
        assert usage["total_tokens"] == 850


class TestInterviewAnswerEvaluation:
    @pytest.mark.asyncio
    async def test_evaluate_answer_high_score(self):
        evaluation = CoachEvaluation(
            score=8.5,
            strengths=["Good specific example", "Clear STAR format"],
            improvements=["Could quantify impact more"],
            coaching_tip="Add metrics to strengthen your answer.",
            sample_answer="A strong sample answer here.",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(evaluation),
        ])

        result = await pipeline.evaluate_interview_answer(
            question="Tell me about a challenge you faced.",
            answer="In my last project, I faced a tight deadline...",
            job_context="Python backend role",
            difficulty=2,
        )

        assert result.score == 8.5
        assert len(result.strengths) == 2
        assert len(result.improvements) == 1

    @pytest.mark.asyncio
    async def test_evaluate_answer_low_score(self):
        evaluation = CoachEvaluation(
            score=3.0,
            strengths=["Attempted to answer"],
            improvements=["Needs specific examples", "Too vague", "No structure"],
            coaching_tip="Use the STAR method.",
            sample_answer="A better structured answer.",
        )

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(evaluation),
        ])

        result = await pipeline.evaluate_interview_answer(
            question="How do you handle conflict?",
            answer="I just deal with it.",
            job_context="Team lead role",
            difficulty=1,
        )

        assert result.score == 3.0


class TestSessionSummary:
    @pytest.mark.asyncio
    async def test_generate_session_summary(self):
        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result("Overall you performed well. Strong technical answers, work on behavioral depth.", total_tokens=100),
        ])

        result = await pipeline.generate_session_summary(
            messages=[{"role": "user", "content": "test"}],
            scores=[7.5, 8.0, 6.5],
        )

        assert isinstance(result, str)
        assert len(result) > 0

        usage = pipeline.get_token_usage()
        assert usage["calls"] == 1


class TestInterviewFixtureValidation:
    @pytest.mark.asyncio
    async def test_pipeline_with_fixture_data(self):
        job_fixture = _load_fixture("analyze_job.json")
        job_analysis = JobAnalysis.model_validate(job_fixture)

        questions_fixture = _load_fixture("interview_questions.json")
        prep = InterviewPrepResult.model_validate(questions_fixture)

        pipeline, _ = _make_pipeline_with_side_effects([
            _ai_result(job_analysis),
            _ai_result(prep),
        ])

        result = await pipeline._execute_interview_prep_pipeline(
            job_description="test",
            candidate_data={},
            ctx={},
        )

        assert result["total_questions"] == 12

        eval_fixture = _load_fixture("evaluate_answer.json")
        evaluation = CoachEvaluation.model_validate(eval_fixture)
        assert evaluation.score == 7.5
        assert len(evaluation.strengths) == 2
