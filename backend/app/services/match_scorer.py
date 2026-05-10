import logging
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from difflib import SequenceMatcher
from sqlalchemy import and_, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.base import ExperienceLevel
from app.models.candidate import CandidateProfile
from app.models.job import Job
from app.models.job_match import JobMatch
from app.models.skill import Skill
from app.models.target_role import TargetRole
from app.services.job_dedup import _normalize_text

logger = logging.getLogger(__name__)

WEIGHTS = {
    "skills": 0.40,
    "experience": 0.25,
    "role_relevance": 0.25,
    "location": 0.10,
}

EXPERIENCE_ORDINAL: dict[str, int] = {
    "student": 0,
    "fresher": 1,
    "junior": 2,
    "mid": 3,
    "senior": 4,
    "lead": 5,
    "executive": 6,
}

SKILL_SIMILARITY_THRESHOLD = 0.6

STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "must",
    "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "me", "him", "her", "us", "them", "my", "your", "his",
    "our", "their", "what", "which", "who", "whom", "when", "where", "why",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
    "too", "very", "just", "because", "as", "until", "while", "if", "then",
    "else", "about", "up", "out", "also", "into", "through", "during",
    "before", "after", "above", "below", "between", "under", "again",
    "further", "once", "here", "there", "any", "over", "work", "working",
    "experience", "including", "well", "using", "etc", "able", "strong",
    "looking", "required", "preferred", "minimum", "plus", "years",
})


@dataclass
class JobMatchResult:
    job_id: uuid.UUID
    match_score: float
    skills_score: float
    experience_score: float
    role_relevance_score: float
    location_score: float
    matched_skills: list[str]
    missing_skills: list[str]

    def to_dict(self) -> dict:
        return {
            "job_id": str(self.job_id),
            "match_score": self.match_score,
            "skills_score": self.skills_score,
            "experience_score": self.experience_score,
            "role_relevance_score": self.role_relevance_score,
            "location_score": self.location_score,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
        }


class MatchScorer:
    def __init__(self, session: AsyncSession, staleness_hours: int = 24):
        self._session = session
        self._staleness_hours = staleness_hours

    async def score_job(self, user_id: str | uuid.UUID, job_id: uuid.UUID) -> JobMatchResult | None:
        profile = await self._load_profile(user_id)
        if profile is None:
            return None

        result = await self._session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return None

        match_result = self._compute_score(profile, job)
        await self._upsert_match(user_id, match_result)
        return match_result

    async def score_jobs_batch(
        self,
        user_id: str | uuid.UUID,
        job_ids: list[uuid.UUID] | None = None,
        chunk_size: int = 100,
    ) -> list[JobMatchResult]:
        profile = await self._load_profile(user_id)
        if profile is None:
            return []

        jobs = await self._get_unscored_jobs(user_id, job_ids)
        if not jobs:
            return []

        all_results: list[JobMatchResult] = []
        start = time.monotonic()

        for i in range(0, len(jobs), chunk_size):
            chunk = jobs[i : i + chunk_size]
            chunk_results: list[JobMatchResult] = []

            for job in chunk:
                result = self._compute_score(profile, job)
                chunk_results.append(result)

            await self._bulk_upsert_matches(user_id, chunk_results)
            all_results.extend(chunk_results)

        duration_ms = round((time.monotonic() - start) * 1000)
        avg_score = (
            sum(r.match_score for r in all_results) / len(all_results)
            if all_results
            else 0.0
        )

        logger.info(
            "batch_scoring_complete",
            extra={
                "user_id": str(user_id),
                "jobs_scored": len(all_results),
                "duration_ms": duration_ms,
                "avg_score": round(avg_score, 2),
            },
        )

        return all_results

    async def get_cached_score(
        self, user_id: str | uuid.UUID, job_id: uuid.UUID
    ) -> JobMatchResult | None:
        result = await self._session.execute(
            select(JobMatch).where(
                and_(
                    JobMatch.user_id == user_id,
                    JobMatch.job_id == job_id,
                )
            )
        )
        cached = result.scalar_one_or_none()
        if cached is None:
            return None

        staleness_cutoff = datetime.utcnow() - timedelta(hours=self._staleness_hours)
        if cached.scored_at < staleness_cutoff:
            return None

        return JobMatchResult(
            job_id=cached.job_id,
            match_score=cached.match_score,
            skills_score=cached.skills_score,
            experience_score=cached.experience_score,
            role_relevance_score=cached.role_relevance_score,
            location_score=cached.location_score,
            matched_skills=cached.matched_skills or [],
            missing_skills=cached.missing_skills or [],
        )

    def _compute_score(self, profile: CandidateProfile, job: Job) -> JobMatchResult:
        skills: list[Skill] = profile.skills if hasattr(profile, "skills") else []
        target_roles: list[TargetRole] = profile.target_roles if hasattr(profile, "target_roles") else []

        skills_score, matched_skills, missing_skills = self._compute_skills_score(skills, job)
        experience_score = self._compute_experience_score(
            profile.experience_level, job.experience_level
        )
        role_relevance_score = self._compute_role_relevance(target_roles, job)
        location_score = self._compute_location_score(profile.location, job)

        match_score = (
            WEIGHTS["skills"] * skills_score
            + WEIGHTS["experience"] * experience_score
            + WEIGHTS["role_relevance"] * role_relevance_score
            + WEIGHTS["location"] * location_score
        ) * 100.0

        return JobMatchResult(
            job_id=job.id,
            match_score=round(match_score, 2),
            skills_score=round(skills_score, 4),
            experience_score=round(experience_score, 4),
            role_relevance_score=round(role_relevance_score, 4),
            location_score=round(location_score, 4),
            matched_skills=matched_skills,
            missing_skills=missing_skills,
        )

    def _compute_skills_score(
        self, skills: list[Skill], job: Job
    ) -> tuple[float, list[str], list[str]]:
        if not skills:
            return 0.0, [], []

        job_keywords = self._extract_keywords(
            f"{job.title or ''} {job.description or ''}"
        )

        if not job_keywords:
            return 0.0, [], [s.name for s in skills]

        matched: list[str] = []
        missing: list[str] = []
        scores: list[float] = []

        for skill in skills:
            skill_norm = _normalize_text(skill.name)
            if not skill_norm:
                continue

            best_score = 0.0
            for keyword in job_keywords:
                ratio = SequenceMatcher(None, skill_norm, keyword).ratio()
                if ratio > best_score:
                    best_score = ratio

            if best_score >= SKILL_SIMILARITY_THRESHOLD:
                matched.append(skill.name)
                scores.append(best_score)
            else:
                missing.append(skill.name)

        avg_score = sum(scores) / len(scores) if scores else 0.0
        return avg_score, matched, missing

    def _compute_experience_score(
        self,
        candidate_level: ExperienceLevel | None,
        job_level: ExperienceLevel | None,
    ) -> float:
        if candidate_level is None or job_level is None:
            return 0.5

        candidate_ordinal = EXPERIENCE_ORDINAL.get(candidate_level.value, 3)
        job_ordinal = EXPERIENCE_ORDINAL.get(job_level.value, 3)
        distance = abs(candidate_ordinal - job_ordinal)

        if distance == 0:
            return 1.0
        elif distance == 1:
            return 0.7
        elif distance == 2:
            return 0.4
        return 0.1

    def _compute_role_relevance(
        self, target_roles: list[TargetRole], job: Job
    ) -> float:
        if not target_roles:
            return 0.0

        job_title_norm = _normalize_text(job.title)
        job_desc_keywords = self._extract_keywords(job.description or "")
        best_score = 0.0

        for role in target_roles:
            role_norm = _normalize_text(role.title)
            if not role_norm:
                continue

            title_ratio = SequenceMatcher(None, job_title_norm, role_norm).ratio()
            if title_ratio > best_score:
                best_score = title_ratio

            role_keywords = self._extract_keywords(role.title)
            if role.keywords:
                role_keywords.extend(self._extract_keywords(role.keywords))

            for rk in role_keywords:
                for dk in job_desc_keywords:
                    ratio = SequenceMatcher(None, rk, dk).ratio()
                    if ratio > best_score:
                        best_score = ratio

        return best_score

    def _compute_location_score(
        self, candidate_location: str | None, job: Job
    ) -> float:
        if job.remote_policy and job.remote_policy.value == "remote":
            return 0.7

        if candidate_location is None or job.location is None:
            return 0.5

        cand_norm = _normalize_text(candidate_location)
        job_norm = _normalize_text(job.location)

        if not cand_norm or not job_norm:
            return 0.5

        if cand_norm == job_norm:
            return 1.0

        cand_parts = set(cand_norm.split(","))
        job_parts = set(job_norm.split(","))

        if cand_parts & job_parts:
            return 0.8

        ratio = SequenceMatcher(None, cand_norm, job_norm).ratio()
        if ratio >= 0.6:
            return 0.8

        return 0.3

    @staticmethod
    def _extract_keywords(text: str) -> list[str]:
        if not text:
            return []

        text_lower = text.lower()
        tokens = re.split(r"[\s\-_,./:;!?()[\]{}\"']+", text_lower)
        tokens = [t for t in tokens if t and t not in STOP_WORDS and len(t) > 1]

        bigrams: list[str] = []
        for i in range(len(tokens) - 1):
            bigram = f"{tokens[i]} {tokens[i + 1]}"
            bigrams.append(bigram)

        return tokens + bigrams

    async def _load_profile(self, user_id: str | uuid.UUID) -> CandidateProfile | None:
        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.user_id == user_id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.target_roles),
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_unscored_jobs(
        self,
        user_id: str | uuid.UUID,
        job_ids: list[uuid.UUID] | None = None,
    ) -> list[Job]:
        staleness_cutoff = datetime.utcnow() - timedelta(hours=self._staleness_hours)

        scored_subquery = select(JobMatch.job_id).where(
            and_(
                JobMatch.user_id == user_id,
                JobMatch.scored_at >= staleness_cutoff,
            )
        )

        stmt = select(Job).where(Job.id.not_in(scored_subquery))

        if job_ids:
            stmt = stmt.where(Job.id.in_(job_ids))

        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def _upsert_match(
        self, user_id: str | uuid.UUID, result: JobMatchResult
    ) -> None:
        stmt = pg_insert(JobMatch).values(
            user_id=user_id,
            job_id=result.job_id,
            match_score=result.match_score,
            skills_score=result.skills_score,
            experience_score=result.experience_score,
            role_relevance_score=result.role_relevance_score,
            location_score=result.location_score,
            matched_skills=result.matched_skills,
            missing_skills=result.missing_skills,
            scored_at=datetime.utcnow(),
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_job_matches_user_job",
            set_={
                "match_score": stmt.excluded.match_score,
                "skills_score": stmt.excluded.skills_score,
                "experience_score": stmt.excluded.experience_score,
                "role_relevance_score": stmt.excluded.role_relevance_score,
                "location_score": stmt.excluded.location_score,
                "matched_skills": stmt.excluded.matched_skills,
                "missing_skills": stmt.excluded.missing_skills,
                "scored_at": stmt.excluded.scored_at,
                "updated_at": datetime.utcnow(),
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def _bulk_upsert_matches(
        self, user_id: str | uuid.UUID, results: list[JobMatchResult]
    ) -> None:
        if not results:
            return

        now = datetime.utcnow()
        values = [
            {
                "user_id": user_id,
                "job_id": r.job_id,
                "match_score": r.match_score,
                "skills_score": r.skills_score,
                "experience_score": r.experience_score,
                "role_relevance_score": r.role_relevance_score,
                "location_score": r.location_score,
                "matched_skills": r.matched_skills,
                "missing_skills": r.missing_skills,
                "scored_at": now,
            }
            for r in results
        ]

        stmt = pg_insert(JobMatch).values(values)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_job_matches_user_job",
            set_={
                "match_score": stmt.excluded.match_score,
                "skills_score": stmt.excluded.skills_score,
                "experience_score": stmt.excluded.experience_score,
                "role_relevance_score": stmt.excluded.role_relevance_score,
                "location_score": stmt.excluded.location_score,
                "matched_skills": stmt.excluded.matched_skills,
                "missing_skills": stmt.excluded.missing_skills,
                "scored_at": stmt.excluded.scored_at,
                "updated_at": now,
            },
        )
        await self._session.execute(stmt)
        await self._session.commit()
