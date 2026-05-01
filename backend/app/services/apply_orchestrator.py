import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models.base import ApplicationStatus
from app.schemas.apply import ApplyOrchestratorResult

logger = logging.getLogger(__name__)

LOCK_PREFIX = "apply_lock:"
PROGRESS_PREFIX = "apply_progress:"

TERMINAL_STATUSES = frozenset({
    ApplicationStatus.applied,
    ApplicationStatus.applied_with_issues,
    ApplicationStatus.manual_required,
    ApplicationStatus.failed,
})


class AutoApplyOrchestrator:
    def __init__(
        self,
        browser_service: Any,
        ai_pipeline: Any,
        session_factory: Callable[[], Coroutine[Any, Any, AsyncSession]],
        redis: Redis,
    ) -> None:
        self._browser = browser_service
        self._pipeline = ai_pipeline
        self._session_factory = session_factory
        self._redis = redis

    async def run(self, application_id: uuid.UUID, user_id: uuid.UUID) -> ApplyOrchestratorResult:
        from app.models.application import Application
        from app.models.job import Job

        start = time.monotonic()
        steps_completed: list[str] = []
        resume_id: uuid.UUID | None = None
        cover_letter_id: uuid.UUID | None = None
        screenshot_path: str | None = None
        manual_url: str | None = None
        error: str | None = None
        final_status = ApplicationStatus.failed

        if not await self._acquire_lock(application_id):
            return ApplyOrchestratorResult(
                application_id=application_id,
                success=False,
                status=ApplicationStatus.failed.value,
                error="Job already in progress (lock held)",
                steps_completed=[],
                total_latency_ms=0,
            )

        try:
            completed_steps = await self._get_completed_steps(application_id)

            async with await self._session_factory() as session:
                result = await session.execute(
                    select(Application).where(Application.id == application_id)
                )
                application = result.scalar_one_or_none()

                if application is None:
                    return ApplyOrchestratorResult(
                        application_id=application_id,
                        success=False,
                        status=ApplicationStatus.failed.value,
                        error="Application not found",
                        steps_completed=[],
                        total_latency_ms=int((time.monotonic() - start) * 1000),
                    )

                job_result = await session.execute(
                    select(Job).where(Job.id == application.job_id)
                )
                job = job_result.scalar_one_or_none()

            if job is None:
                await self._update_status(application_id, ApplicationStatus.failed, ats_detection_error="Job not found")
                return ApplyOrchestratorResult(
                    application_id=application_id,
                    success=False,
                    status=ApplicationStatus.failed.value,
                    error="Job not found",
                    steps_completed=steps_completed,
                    total_latency_ms=int((time.monotonic() - start) * 1000),
                )

            if "load_profile" not in completed_steps:
                profile = await self._load_profile(user_id)
                await self._record_step(application_id, "load_profile")
                steps_completed.append("load_profile")
            else:
                profile = await self._load_profile(user_id)
                steps_completed.append("load_profile")

            if "generate_resume" not in completed_steps:
                resume = await self._generate_resume(application_id, job, profile)
                resume_id = resume.id if resume else None
                await self._record_step(application_id, "generate_resume", resume_id=str(resume_id) if resume_id else None)
                steps_completed.append("generate_resume")
            else:
                resume = await self._get_existing_resume(application_id, user_id)
                resume_id = resume.id if resume else None
                steps_completed.append("generate_resume")

            if resume is None:
                await self._update_status(application_id, ApplicationStatus.failed, ats_detection_error="Resume generation failed")
                return ApplyOrchestratorResult(
                    application_id=application_id,
                    success=False,
                    status=ApplicationStatus.failed.value,
                    error="Resume generation failed",
                    steps_completed=steps_completed,
                    total_latency_ms=int((time.monotonic() - start) * 1000),
                )

            resume_path = await self._save_resume_to_file(resume, application_id)
            await self._record_step(application_id, "save_resume")
            steps_completed.append("save_resume")

            if "generate_cover_letter" not in completed_steps:
                cover_letter = await self._generate_cover_letter(application_id, job, profile)
                cover_letter_id = cover_letter.id if cover_letter else None
                await self._record_step(
                    application_id, "generate_cover_letter",
                    cover_letter_id=str(cover_letter_id) if cover_letter_id else None,
                )
                steps_completed.append("generate_cover_letter")
            else:
                cover_letter = await self._get_existing_cover_letter(application_id, user_id)
                cover_letter_id = cover_letter.id if cover_letter else None
                steps_completed.append("generate_cover_letter")

            apply_result = await self._attempt_ats_apply(application_id, job, profile, resume_path)
            screenshot_path = apply_result.get("screenshot_path")
            manual_url = apply_result.get("manual_url")
            final_status = apply_result["status"]

            status_kwargs: dict[str, Any] = {
                "ats_screenshot_path": screenshot_path,
                "ats_form_url": manual_url,
            }
            if final_status == ApplicationStatus.applied:
                status_kwargs["applied_at"] = datetime.now(timezone.utc)

            await self._update_status(application_id, final_status, **status_kwargs)
            steps_completed.append("ats_apply")

            return ApplyOrchestratorResult(
                application_id=application_id,
                success=final_status == ApplicationStatus.applied,
                status=final_status.value,
                resume_id=resume_id,
                cover_letter_id=cover_letter_id,
                screenshot_path=screenshot_path,
                manual_url=manual_url,
                error=error,
                steps_completed=steps_completed,
                total_latency_ms=int((time.monotonic() - start) * 1000),
            )

        except Exception as exc:
            logger.error(
                "apply_orchestrator_error",
                extra={
                    "application_id": str(application_id),
                    "user_id": str(user_id),
                    "error": str(exc),
                    "steps_completed": steps_completed,
                },
                exc_info=True,
            )
            await self._update_status(
                application_id,
                ApplicationStatus.failed,
                ats_detection_error=str(exc),
            )
            return ApplyOrchestratorResult(
                application_id=application_id,
                success=False,
                status=ApplicationStatus.failed.value,
                error=str(exc),
                steps_completed=steps_completed,
                total_latency_ms=int((time.monotonic() - start) * 1000),
            )

        finally:
            await self._release_lock(application_id)

    async def _acquire_lock(self, application_id: uuid.UUID) -> bool:
        key = f"{LOCK_PREFIX}{application_id}"
        ttl = settings.ATS_APPLY_STALE_MINUTES * 60
        return await self._redis.set(key, "1", nx=True, ex=ttl)

    async def _release_lock(self, application_id: uuid.UUID) -> None:
        key = f"{LOCK_PREFIX}{application_id}"
        await self._redis.delete(key)

    async def _get_completed_steps(self, application_id: uuid.UUID) -> list[str]:
        key = f"{PROGRESS_PREFIX}{application_id}"
        raw = await self._redis.get(key)
        if raw is None:
            return []
        try:
            data = json.loads(raw)
            return data.get("steps_completed", [])
        except (json.JSONDecodeError, TypeError):
            return []

    async def _record_step(self, application_id: uuid.UUID, step: str, **extra: Any) -> None:
        key = f"{PROGRESS_PREFIX}{application_id}"
        raw = await self._redis.get(key)
        data: dict[str, Any] = {}
        if raw:
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                data = {}

        steps = data.get("steps_completed", [])
        if step not in steps:
            steps.append(step)
        data["steps_completed"] = steps
        data["current_step"] = step
        data.update(extra)

        await self._redis.set(key, json.dumps(data), ex=86400)

        logger.info(
            "apply_step_completed",
            extra={
                "application_id": str(application_id),
                "step": step,
            },
        )

    async def _load_profile(self, user_id: uuid.UUID) -> Any:
        from app.models.candidate import CandidateProfile

        async with await self._session_factory() as session:
            stmt = (
                select(CandidateProfile)
                .where(CandidateProfile.user_id == user_id)
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
            raise ValueError(f"Candidate profile not found for user {user_id}")
        return profile

    async def _generate_resume(self, application_id: uuid.UUID, job: Any, profile: Any) -> Any:
        from app.models.resume import Resume

        step_start = time.monotonic()

        try:
            job_description = job.description or ""
            pipeline_result = await self._pipeline.run_full_pipeline(
                job_description=job_description,
                candidate_profile_id=str(profile.id),
                user_id=str(profile.user_id),
            )

            resume_data = pipeline_result.get("resume", {})
            ats_result = pipeline_result.get("ats_result", {})

            async with await self._session_factory() as session:
                resume = Resume(
                    user_id=profile.user_id,
                    job_id=job.id,
                    content_json=resume_data,
                    ats_score=ats_result.get("overall_score"),
                    ats_breakdown=ats_result,
                    status="completed",
                )
                session.add(resume)
                await session.commit()
                await session.refresh(resume)

            logger.info(
                "resume_generated",
                extra={
                    "application_id": str(application_id),
                    "resume_id": str(resume.id),
                    "ats_score": ats_result.get("overall_score"),
                    "latency_ms": int((time.monotonic() - step_start) * 1000),
                },
            )
            return resume

        except Exception as exc:
            logger.error(
                f"Resume generation failed for application {application_id}: {exc}",
                exc_info=True,
            )
            await self._update_status(
                application_id,
                ApplicationStatus.failed,
                ats_detection_error=f"Resume generation failed: {exc}",
            )
            raise

    async def _generate_cover_letter(self, application_id: uuid.UUID, job: Any, profile: Any) -> Any | None:
        from app.models.cover_letter import CoverLetter

        step_start = time.monotonic()

        try:
            job_description = job.description or ""
            pipeline_result = await self._pipeline.run_cover_letter_pipeline(
                job_description=job_description,
                candidate_profile_id=str(profile.id),
                user_id=str(profile.user_id),
            )

            cover_letter_data = pipeline_result.get("cover_letter", {})

            async with await self._session_factory() as session:
                cover_letter = CoverLetter(
                    user_id=profile.user_id,
                    job_id=job.id,
                    job_description=job_description,
                    content=cover_letter_data.get("full_text", ""),
                    content_json=cover_letter_data,
                    tone=cover_letter_data.get("tone_used", "professional"),
                    status="completed",
                )
                session.add(cover_letter)
                await session.commit()
                await session.refresh(cover_letter)

            logger.info(
                "cover_letter_generated",
                extra={
                    "application_id": str(application_id),
                    "cover_letter_id": str(cover_letter.id),
                    "latency_ms": int((time.monotonic() - step_start) * 1000),
                },
            )
            return cover_letter

        except Exception as exc:
            logger.warning(
                f"Cover letter generation failed for application {application_id}: {exc}",
                extra={"application_id": str(application_id)},
            )
            return None

    async def _save_resume_to_file(self, resume: Any, application_id: uuid.UUID) -> str:
        resume_dir = settings.ATS_RESUME_DIR
        os.makedirs(resume_dir, exist_ok=True)

        filename = f"{application_id}.{settings.ATS_RESUME_FILE_FORMAT}"
        filepath = os.path.join(resume_dir, filename)

        content_json = resume.content_json or {}
        content_str = json.dumps(content_json, indent=2) if isinstance(content_json, dict) else str(content_json)

        resolved = os.path.realpath(filepath)
        resume_dir_resolved = os.path.realpath(resume_dir)
        if not resolved.startswith(resume_dir_resolved):
            raise ValueError("Path traversal detected in resume file path")

        with open(resolved, "w") as f:
            f.write(content_str)

        return resolved

    async def _get_existing_resume(self, application_id: uuid.UUID, user_id: uuid.UUID) -> Any | None:
        from app.models.application import Application
        from app.models.resume import Resume

        async with await self._session_factory() as session:
            app_result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            application = app_result.scalar_one_or_none()
            if application is None:
                return None

            result = await session.execute(
                select(Resume)
                .where(Resume.user_id == user_id, Resume.job_id == application.job_id)
                .order_by(Resume.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _get_existing_cover_letter(self, application_id: uuid.UUID, user_id: uuid.UUID) -> Any | None:
        from app.models.application import Application
        from app.models.cover_letter import CoverLetter

        async with await self._session_factory() as session:
            app_result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            application = app_result.scalar_one_or_none()
            if application is None:
                return None

            result = await session.execute(
                select(CoverLetter)
                .where(CoverLetter.user_id == user_id, CoverLetter.job_id == application.job_id)
                .order_by(CoverLetter.created_at.desc())
                .limit(1)
            )
            return result.scalar_one_or_none()

    async def _attempt_ats_apply(
        self,
        application_id: uuid.UUID,
        job: Any,
        profile: Any,
        resume_path: str,
    ) -> dict[str, Any]:
        from app.models.application import Application
        from app.services.ats_fillers.exceptions import ATSCAPTCHAError
        from app.services.ats_fillers.registry import ATSFillerRegistry

        async with await self._session_factory() as session:
            result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            application = result.scalar_one_or_none()

            if application is None:
                return {
                    "status": ApplicationStatus.failed,
                    "error": "Application not found",
                }

        ats_platform = application.ats_platform

        if not ats_platform:
            logger.info(
                "no_ats_platform_manual_required",
                extra={"application_id": str(application_id)},
            )
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": job.apply_url,
            }

        registry = ATSFillerRegistry(self._browser)
        filler = registry.get_filler(ats_platform)

        if filler is None:
            logger.info(
                "unsupported_ats_platform",
                extra={"application_id": str(application_id), "ats_platform": ats_platform},
            )
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": job.apply_url,
            }

        apply_url = application.ats_form_url or job.apply_url or ""
        if not apply_url:
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": None,
            }

        try:
            page = await self._browser.new_page()
            try:
                await self._browser.safe_goto(page, apply_url)

                await self._record_step(application_id, "filling_form")
                await filler.fill(page, profile, resume_path=resume_path)

                await self._record_step(application_id, "submitting")
                submitted = await filler.submit(page)

                if not submitted:
                    screenshot_path = await self._browser.capture_screenshot(page, f"submit_failed_{application_id}")
                    return {
                        "status": ApplicationStatus.manual_required,
                        "screenshot_path": screenshot_path,
                        "manual_url": apply_url,
                    }

                await self._record_step(application_id, "verifying")
                verify_result = await filler.verify(page)

                screenshot_path = await self._browser.capture_screenshot(page, f"apply_{application_id}")

                if verify_result.success:
                    return {
                        "status": ApplicationStatus.applied,
                        "screenshot_path": verify_result.screenshot_path or screenshot_path,
                    }
                else:
                    return {
                        "status": ApplicationStatus.applied_with_issues,
                        "screenshot_path": verify_result.screenshot_path or screenshot_path,
                        "manual_url": apply_url,
                    }

            except ATSCAPTCHAError:
                screenshot_path = await self._browser.capture_screenshot(page, f"captcha_{application_id}")
                return {
                    "status": ApplicationStatus.manual_required,
                    "screenshot_path": screenshot_path,
                    "manual_url": apply_url,
                }
            finally:
                await self._browser.close_page(page)

        except Exception as exc:
            logger.error(
                f"ATS apply failed for application {application_id}: {exc}",
                exc_info=True,
            )
            return {
                "status": ApplicationStatus.manual_required,
                "manual_url": job.apply_url,
                "error": str(exc),
            }

    async def _update_status(self, application_id: uuid.UUID, status: ApplicationStatus, **kwargs: Any) -> None:
        from app.models.application import Application

        async with await self._session_factory() as session:
            result = await session.execute(
                select(Application).where(Application.id == application_id)
            )
            application = result.scalar_one_or_none()
            if application is None:
                return

            application.status = status
            for key, value in kwargs.items():
                if value is not None and hasattr(application, key):
                    setattr(application, key, value)

            session.add(application)
            await session.commit()

        logger.info(
            "apply_status_updated",
            extra={
                "application_id": str(application_id),
                "status": status.value,
                **{k: str(v) for k, v in kwargs.items() if v is not None},
            },
        )
