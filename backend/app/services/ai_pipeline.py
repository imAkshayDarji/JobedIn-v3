import asyncio
import json
import logging
import time
from typing import Any, Callable, Coroutine

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.services.ai_client import (
    AIClient,
    AIPipelineError,
)
from app.services.ai_prompts import (
    analyze_job_prompt,
    ats_retry_prompt,
    gap_analysis_prompt,
    generate_resume_prompt,
    validate_ats_prompt,
)
from app.schemas.ai import (
    ATSResult,
    GapAnalysis,
    JobAnalysis,
    ResumeContent,
)

logger = logging.getLogger(__name__)

MAX_ATS_RETRIES = 2
ATS_PASS_THRESHOLD = 80.0


class AIPipeline:
    def __init__(
        self,
        ai_client: AIClient | None = None,
        session_factory: Callable[[], Coroutine[Any, Any, AsyncSession]] | None = None,
    ) -> None:
        self._client = ai_client or AIClient()
        self._session_factory = session_factory

    async def _get_session(self) -> AsyncSession:
        if self._session_factory is None:
            raise AIPipelineError("No session factory configured")
        return await self._session_factory()

    async def analyze_job(self, job_description: str, context: dict[str, Any] | None = None) -> JobAnalysis:
        log_ctx = {"pipeline_step": "analyze_job", **(context or {})}
        start = time.monotonic()
        result = await self._client.call(
            task="analyze_job",
            messages=analyze_job_prompt(job_description),
            response_model=JobAnalysis,
            context=log_ctx,
        )
        latency_ms = (time.monotonic() - start) * 1000
        logger.info("analyze_job complete", extra={**log_ctx, "latency_ms": latency_ms})
        return result

    async def gap_analysis(
        self,
        job_analysis: JobAnalysis,
        candidate_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> GapAnalysis:
        log_ctx = {"pipeline_step": "gap_analysis", **(context or {})}
        start = time.monotonic()
        result = await self._client.call(
            task="gap_analysis",
            messages=gap_analysis_prompt(
                job_analysis_json=job_analysis.model_dump_json(),
                candidate_profile_json=json.dumps(candidate_data),
            ),
            response_model=GapAnalysis,
            context=log_ctx,
        )
        latency_ms = (time.monotonic() - start) * 1000
        logger.info("gap_analysis complete", extra={**log_ctx, "latency_ms": latency_ms})
        return result

    async def generate_resume(
        self,
        job_analysis: JobAnalysis,
        gap_analysis: GapAnalysis,
        candidate_data: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> ResumeContent:
        log_ctx = {"pipeline_step": "generate_resume", **(context or {})}
        start = time.monotonic()
        result = await self._client.call(
            task="generate_resume",
            messages=generate_resume_prompt(
                job_analysis_json=job_analysis.model_dump_json(),
                gap_analysis_json=gap_analysis.model_dump_json(),
                candidate_profile_json=json.dumps(candidate_data),
            ),
            response_model=ResumeContent,
            context=log_ctx,
        )
        latency_ms = (time.monotonic() - start) * 1000
        logger.info("generate_resume complete", extra={**log_ctx, "latency_ms": latency_ms})
        return result

    async def validate_ats(
        self,
        resume: ResumeContent,
        job_analysis: JobAnalysis,
        context: dict[str, Any] | None = None,
    ) -> ATSResult:
        log_ctx = {"pipeline_step": "validate_ats", **(context or {})}
        start = time.monotonic()
        result = await self._client.call(
            task="validate_ats",
            messages=validate_ats_prompt(
                resume_json=resume.model_dump_json(),
                job_analysis_json=job_analysis.model_dump_json(),
            ),
            response_model=ATSResult,
            context=log_ctx,
        )
        latency_ms = (time.monotonic() - start) * 1000
        logger.info("validate_ats complete", extra={**log_ctx, "latency_ms": latency_ms})
        return result

    async def run_full_pipeline(
        self,
        job_description: str,
        candidate_profile_id: str,
        user_id: str,
        get_session: Callable[[], Coroutine[Any, Any, AsyncSession]] | None = None,
    ) -> dict[str, Any]:
        session_factory = get_session or self._session_factory
        if session_factory is None:
            raise AIPipelineError("No session factory provided")

        async with await session_factory() as session:
            await self._verify_ownership(session, candidate_profile_id, user_id)
            candidate_data = await self._load_candidate(session, candidate_profile_id)

        ctx: dict[str, Any] = {
            "job_id": None,
            "user_id": user_id,
            "candidate_id": candidate_profile_id,
        }

        try:
            result = await asyncio.wait_for(
                self._execute_pipeline(job_description, candidate_data, ctx),
                timeout=float(settings.AI_PIPELINE_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            logger.error("Pipeline timed out", extra=ctx)
            raise AIPipelineError(f"Pipeline timed out after {settings.AI_PIPELINE_TIMEOUT_SECONDS}s")

        return result

    async def _execute_pipeline(
        self,
        job_description: str,
        candidate_data: dict[str, Any],
        ctx: dict[str, Any],
    ) -> dict[str, Any]:
        job_analysis = await self.analyze_job(job_description, context=ctx)

        gap = await self.gap_analysis(job_analysis, candidate_data, context=ctx)

        resume = await self.generate_resume(job_analysis, gap, candidate_data, context=ctx)

        for attempt in range(MAX_ATS_RETRIES):
            ats_result = await self.validate_ats(resume, job_analysis, context=ctx)

            if ats_result.overall_score >= ATS_PASS_THRESHOLD:
                break

            logger.info(
                f"ATS score {ats_result.overall_score} < {ATS_PASS_THRESHOLD}, retry {attempt + 1}",
                extra=ctx,
            )

            retry_result = await self._client.call(
                task="generate_resume",
                messages=ats_retry_prompt(
                    resume_json=resume.model_dump_json(),
                    ats_result_json=ats_result.model_dump_json(),
                    job_analysis_json=job_analysis.model_dump_json(),
                ),
                response_model=ResumeContent,
                context={**ctx, "pipeline_step": "ats_retry"},
            )
            resume = retry_result
        else:
            ats_result = await self.validate_ats(resume, job_analysis, context=ctx)

        return {
            "job_analysis": job_analysis.model_dump(),
            "gap_analysis": gap.model_dump(),
            "resume": resume.model_dump(),
            "ats_result": ats_result.model_dump(),
        }

    async def _verify_ownership(
        self, session: AsyncSession, candidate_profile_id: str, user_id: str
    ) -> None:
        from app.models.candidate import CandidateProfile

        result = await session.execute(
            select(CandidateProfile).where(CandidateProfile.id == candidate_profile_id)
        )
        profile = result.scalar_one_or_none()
        if profile is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate profile not found",
            )
        if str(profile.user_id) != str(user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not own this candidate profile",
            )

    async def _load_candidate(
        self, session: AsyncSession, candidate_profile_id: str
    ) -> dict[str, Any]:
        from app.models.candidate import CandidateProfile

        stmt = (
            select(CandidateProfile)
            .where(CandidateProfile.id == candidate_profile_id)
            .options(
                selectinload(CandidateProfile.skills),
                selectinload(CandidateProfile.education),
                selectinload(CandidateProfile.experience),
                selectinload(CandidateProfile.projects),
                selectinload(CandidateProfile.target_roles),
                selectinload(CandidateProfile.certifications),
                selectinload(CandidateProfile.languages),
            )
        )
        result = await session.execute(stmt)
        profile = result.scalar_one_or_none()
        if profile is None:
            raise AIPipelineError(f"Candidate profile {candidate_profile_id} not found")

        data: dict[str, Any] = {
            "id": str(profile.id),
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "headline": profile.headline,
            "summary": profile.summary,
            "location": profile.location,
            "experience_level": profile.experience_level,
        }

        data["skills"] = [
            {"name": s.name, "category": s.category, "proficiency": s.proficiency}
            for s in profile.skills
        ]
        data["education"] = [
            {
                "institution": e.institution,
                "degree": e.degree,
                "field_of_study": e.field_of_study,
                "start_date": str(e.start_date) if e.start_date else None,
                "end_date": str(e.end_date) if e.end_date else None,
                "grade": e.grade,
                "description": e.description,
            }
            for e in profile.education
        ]
        data["experience"] = [
            {
                "company": ex.company,
                "title": ex.title,
                "location": ex.location,
                "start_date": str(ex.start_date) if ex.start_date else None,
                "end_date": str(ex.end_date) if ex.end_date else None,
                "description": ex.description,
                "is_current": ex.is_current,
            }
            for ex in profile.experience
        ]
        data["projects"] = [
            {
                "name": p.name,
                "description": p.description,
                "url": p.url,
                "technologies": p.technologies,
            }
            for p in profile.projects
        ]
        data["target_roles"] = [
            {"title": tr.title, "priority": tr.priority, "keywords": tr.keywords}
            for tr in profile.target_roles
        ]
        data["certifications"] = [
            {
                "name": c.name,
                "issuer": c.issuer,
                "issue_date": str(c.issue_date) if c.issue_date else None,
                "expiry_date": str(c.expiry_date) if c.expiry_date else None,
                "credential_url": c.credential_url,
            }
            for c in profile.certifications
        ]
        data["languages"] = [
            {"name": lang.name, "proficiency": lang.proficiency}
            for lang in profile.languages
        ]

        return data



