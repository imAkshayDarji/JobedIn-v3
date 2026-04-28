"""Tests for the match scoring engine.

Covers:
- Keyword extraction (3 tests)
- Skills score (3 tests)
- Experience score (4 tests)
- Role relevance (2 tests)
- Location score (3 tests)
- Weighted combination (1 test)
- score_job (2 tests)
- score_jobs_batch (2 tests)
- get_cached_score (2 tests)
"""

import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ExperienceLevel, RemotePolicy
from app.services.match_scorer import (
    EXPERIENCE_ORDINAL,
    SKILL_SIMILARITY_THRESHOLD,
    STOP_WORDS,
    WEIGHTS,
    JobMatchResult,
    MatchScorer,
)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_job(
    title: str = "Software Engineer",
    company: str = "Acme Corp",
    description: str | None = None,
    experience_level: ExperienceLevel | None = None,
    location: str | None = "San Francisco, CA",
    remote_policy: RemotePolicy | None = None,
    job_id: uuid.UUID | None = None,
):
    job = MagicMock()
    job.id = job_id or uuid.uuid4()
    job.title = title
    job.company = company
    job.description = description
    job.experience_level = experience_level
    job.location = location
    job.remote_policy = remote_policy
    return job


def _make_skill(name: str, category: str | None = None):
    skill = MagicMock()
    skill.name = name
    skill.category = category
    return skill


def _make_target_role(title: str, keywords: str | None = None, priority: int = 0):
    role = MagicMock()
    role.title = title
    role.keywords = keywords
    role.priority = priority
    return role


def _make_profile(
    skills: list | None = None,
    target_roles: list | None = None,
    experience_level: ExperienceLevel | None = None,
    location: str | None = "San Francisco, CA",
):
    profile = MagicMock()
    profile.skills = skills or []
    profile.target_roles = target_roles or []
    profile.experience_level = experience_level
    profile.location = location
    return profile


def _create_scorer() -> MatchScorer:
    session = AsyncMock()
    return MatchScorer(session)


# ── Keyword Extraction ───────────────────────────────────────────────────────


class TestExtractKeywords:
    def test_normal_text(self):
        result = MatchScorer._extract_keywords(
            "We are looking for a Python developer with machine learning experience"
        )
        assert "python" in result
        assert "developer" in result
        assert "machine" in result
        assert "learning" in result
        assert "machine learning" in result
        assert "looking" not in result
        assert "the" not in result

    def test_empty_text(self):
        result = MatchScorer._extract_keywords("")
        assert result == []

    def test_multi_word_skills(self):
        result = MatchScorer._extract_keywords(
            "project management data analysis quality assurance"
        )
        assert "project management" in result
        assert "data analysis" in result
        assert "quality assurance" in result


# ── Skills Score ─────────────────────────────────────────────────────────────


class TestSkillsScore:
    def test_normal_match(self):
        scorer = _create_scorer()
        skills = [_make_skill("Python"), _make_skill("JavaScript"), _make_skill("SQL")]
        job = _make_job(
            title="Python Developer",
            description="We need a developer with Python and SQL skills",
        )

        score, matched, missing = scorer._compute_skills_score(skills, job)

        assert "Python" in matched
        assert "SQL" in matched
        assert score > 0.5

    def test_empty_skills(self):
        scorer = _create_scorer()
        job = _make_job(title="Developer", description="Python developer")

        score, matched, missing = scorer._compute_skills_score([], job)

        assert score == 0.0
        assert matched == []
        assert missing == []

    def test_multi_word_matching(self):
        scorer = _create_scorer()
        skills = [_make_skill("Machine Learning"), _make_skill("Data Analysis")]
        job = _make_job(
            title="ML Engineer",
            description="Experience with machine learning and data analysis required",
        )

        score, matched, missing = scorer._compute_skills_score(skills, job)

        assert "Machine Learning" in matched
        assert "Data Analysis" in matched


# ── Experience Score ─────────────────────────────────────────────────────────


class TestExperienceScore:
    def test_same_level(self):
        scorer = _create_scorer()
        score = scorer._compute_experience_score(ExperienceLevel.senior, ExperienceLevel.senior)
        assert score == 1.0

    def test_one_step_apart(self):
        scorer = _create_scorer()
        score = scorer._compute_experience_score(ExperienceLevel.senior, ExperienceLevel.lead)
        assert score == 0.7

    def test_two_steps_apart(self):
        scorer = _create_scorer()
        score = scorer._compute_experience_score(ExperienceLevel.junior, ExperienceLevel.senior)
        assert score == 0.4

    def test_missing_levels(self):
        scorer = _create_scorer()
        score_none_both = scorer._compute_experience_score(None, None)
        assert score_none_both == 0.5

        score_none_candidate = scorer._compute_experience_score(None, ExperienceLevel.mid)
        assert score_none_candidate == 0.5

        score_none_job = scorer._compute_experience_score(ExperienceLevel.mid, None)
        assert score_none_job == 0.5


# ── Role Relevance ───────────────────────────────────────────────────────────


class TestRoleRelevance:
    def test_match_found(self):
        scorer = _create_scorer()
        roles = [_make_target_role("Software Engineer"), _make_target_role("Data Scientist")]
        job = _make_job(title="Senior Software Engineer", description="Build scalable systems")

        score = scorer._compute_role_relevance(roles, job)

        assert score > 0.5

    def test_no_target_roles(self):
        scorer = _create_scorer()
        job = _make_job(title="Software Engineer")

        score = scorer._compute_role_relevance([], job)

        assert score == 0.0


# ── Location Score ───────────────────────────────────────────────────────────


class TestLocationScore:
    def test_exact_match(self):
        scorer = _create_scorer()
        score = scorer._compute_location_score("San Francisco, CA", _make_job(location="San Francisco, CA"))
        assert score == 1.0

    def test_remote_job(self):
        scorer = _create_scorer()
        job = _make_job(remote_policy=RemotePolicy.remote)
        score = scorer._compute_location_score("San Francisco, CA", job)
        assert score == 0.7

    def test_missing_location(self):
        scorer = _create_scorer()
        score_both_none = scorer._compute_location_score(None, _make_job(location=None))
        assert score_both_none == 0.5

        score_cand_none = scorer._compute_location_score(None, _make_job(location="NYC"))
        assert score_cand_none == 0.5


# ── Weighted Combination ────────────────────────────────────────────────────


class TestWeightedCombination:
    def test_all_dimensions(self):
        scorer = _create_scorer()
        profile = _make_profile(
            skills=[_make_skill("Python")],
            target_roles=[_make_target_role("Software Engineer")],
            experience_level=ExperienceLevel.senior,
            location="San Francisco, CA",
        )
        job = _make_job(
            title="Senior Software Engineer",
            description="Python development",
            experience_level=ExperienceLevel.senior,
            location="San Francisco, CA",
        )

        result = scorer._compute_score(profile, job)

        assert result.match_score > 50.0
        assert 0.0 <= result.skills_score <= 1.0
        assert 0.0 <= result.experience_score <= 1.0
        assert 0.0 <= result.role_relevance_score <= 1.0
        assert 0.0 <= result.location_score <= 1.0

        expected = (
            WEIGHTS["skills"] * result.skills_score
            + WEIGHTS["experience"] * result.experience_score
            + WEIGHTS["role_relevance"] * result.role_relevance_score
            + WEIGHTS["location"] * result.location_score
        ) * 100.0
        assert abs(result.match_score - round(expected, 2)) < 0.01


# ── score_job ────────────────────────────────────────────────────────────────


class TestScoreJob:
    @pytest.mark.asyncio
    async def test_happy_path(self):
        scorer = _create_scorer()
        profile = _make_profile(
            skills=[_make_skill("Python")],
            target_roles=[_make_target_role("Software Engineer")],
            experience_level=ExperienceLevel.mid,
            location="NYC",
        )

        job = _make_job(
            title="Software Engineer",
            description="Python developer",
            experience_level=ExperienceLevel.mid,
            location="NYC",
        )

        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = profile

        mock_job_result = MagicMock()
        mock_job_result.scalar_one_or_none.return_value = job

        mock_upsert_result = MagicMock()
        scorer._session.execute = AsyncMock(side_effect=[mock_profile_result, mock_job_result, mock_upsert_result])
        scorer._session.commit = AsyncMock()

        result = await scorer.score_job(uuid.uuid4(), job.id)

        assert result is not None
        assert result.job_id == job.id
        assert result.match_score > 0

    @pytest.mark.asyncio
    async def test_profile_not_found(self):
        scorer = _create_scorer()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        scorer._session.execute = AsyncMock(return_value=mock_result)

        result = await scorer.score_job(uuid.uuid4(), uuid.uuid4())

        assert result is None


# ── score_jobs_batch ─────────────────────────────────────────────────────────


class TestScoreJobsBatch:
    @pytest.mark.asyncio
    async def test_batch_of_jobs(self):
        scorer = _create_scorer()
        profile = _make_profile(
            skills=[_make_skill("Python")],
            target_roles=[_make_target_role("Engineer")],
            experience_level=ExperienceLevel.mid,
            location="NYC",
        )

        jobs = [_make_job(title=f"Engineer {i}", description="Python dev") for i in range(5)]

        mock_profile_result = MagicMock()
        mock_profile_result.scalar_one_or_none.return_value = profile

        mock_jobs_result = MagicMock()
        mock_jobs_result.scalars.return_value.all.return_value = jobs

        mock_upsert_result = MagicMock()
        scorer._session.execute = AsyncMock(side_effect=[mock_profile_result, mock_jobs_result, mock_upsert_result])
        scorer._session.commit = AsyncMock()

        results = await scorer.score_jobs_batch(uuid.uuid4())

        assert len(results) == 5
        assert all(r.match_score >= 0 for r in results)

    @pytest.mark.asyncio
    async def test_batch_no_profile(self):
        scorer = _create_scorer()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        scorer._session.execute = AsyncMock(return_value=mock_result)

        results = await scorer.score_jobs_batch(uuid.uuid4())

        assert results == []


# ── get_cached_score ─────────────────────────────────────────────────────────


class TestGetCachedScore:
    @pytest.mark.asyncio
    async def test_cache_hit(self):
        scorer = _create_scorer()
        cached = MagicMock()
        cached.job_id = uuid.uuid4()
        cached.match_score = 85.0
        cached.skills_score = 0.9
        cached.experience_score = 1.0
        cached.role_relevance_score = 0.8
        cached.location_score = 1.0
        cached.matched_skills = ["Python"]
        cached.missing_skills = ["Java"]
        cached.scored_at = datetime.utcnow()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached
        scorer._session.execute = AsyncMock(return_value=mock_result)

        result = await scorer.get_cached_score(uuid.uuid4(), cached.job_id)

        assert result is not None
        assert result.match_score == 85.0
        assert "Python" in result.matched_skills

    @pytest.mark.asyncio
    async def test_stale_rescore(self):
        scorer = _create_scorer()
        cached = MagicMock()
        cached.job_id = uuid.uuid4()
        cached.scored_at = datetime.utcnow() - timedelta(hours=48)

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = cached
        scorer._session.execute = AsyncMock(return_value=mock_result)

        result = await scorer.get_cached_score(uuid.uuid4(), cached.job_id)

        assert result is None


# ── Experience Ordinal Mapping ───────────────────────────────────────────────


class TestExperienceOrdinal:
    def test_all_levels_mapped(self):
        expected = ["student", "fresher", "junior", "mid", "senior", "lead", "executive"]
        for level in expected:
            assert level in EXPERIENCE_ORDINAL

    def test_ordinal_ordering(self):
        assert EXPERIENCE_ORDINAL["student"] < EXPERIENCE_ORDINAL["fresher"]
        assert EXPERIENCE_ORDINAL["junior"] < EXPERIENCE_ORDINAL["mid"]
        assert EXPERIENCE_ORDINAL["senior"] < EXPERIENCE_ORDINAL["lead"]


# ── Stop Words ───────────────────────────────────────────────────────────────


class TestStopWords:
    def test_common_words_in_stop_list(self):
        assert "the" in STOP_WORDS
        assert "and" in STOP_WORDS
        assert "or" in STOP_WORDS
        assert "with" in STOP_WORDS

    def test_skill_words_not_in_stop_list(self):
        assert "python" not in STOP_WORDS
        assert "javascript" not in STOP_WORDS
        assert "machine" not in STOP_WORDS
        assert "engineering" not in STOP_WORDS


# ── JobMatchResult ───────────────────────────────────────────────────────────


class TestJobMatchResultToDict:
    def test_to_dict(self):
        result = JobMatchResult(
            job_id=uuid.uuid4(),
            match_score=75.5,
            skills_score=0.8,
            experience_score=1.0,
            role_relevance_score=0.7,
            location_score=0.5,
            matched_skills=["Python"],
            missing_skills=["Java"],
        )

        d = result.to_dict()

        assert "job_id" in d
        assert d["match_score"] == 75.5
        assert d["matched_skills"] == ["Python"]
        assert d["missing_skills"] == ["Java"]


# ── Weights ──────────────────────────────────────────────────────────────────


class TestWeights:
    def test_weights_sum_to_one(self):
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 0.001

    def test_weight_distribution(self):
        assert WEIGHTS["skills"] == 0.40
        assert WEIGHTS["experience"] == 0.25
        assert WEIGHTS["role_relevance"] == 0.25
        assert WEIGHTS["location"] == 0.10
