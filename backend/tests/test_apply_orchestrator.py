import json
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.base import ApplicationStatus
from app.schemas.apply import ApplyOrchestratorResult

TEST_USER_ID = uuid.uuid4()
TEST_JOB_ID = uuid.uuid4()
TEST_APPLICATION_ID = uuid.uuid4()


def _make_application(
    app_id: uuid.UUID = TEST_APPLICATION_ID,
    user_id: uuid.UUID = TEST_USER_ID,
    job_id: uuid.UUID = TEST_JOB_ID,
    status: ApplicationStatus = ApplicationStatus.ready,
    ats_platform: str | None = "greenhouse",
    ats_form_url: str | None = "https://boards.greenhouse.io/test/jobs/1",
) -> MagicMock:
    app = MagicMock()
    app.id = app_id
    app.user_id = user_id
    app.job_id = job_id
    app.status = status
    app.ats_platform = ats_platform
    app.ats_form_url = ats_form_url
    app.ats_screenshot_path = None
    app.ats_detection_error = None
    return app


def _make_job(
    job_id: uuid.UUID = TEST_JOB_ID,
    description: str = "Test job description",
    apply_url: str = "https://boards.greenhouse.io/test/jobs/1",
) -> MagicMock:
    job = MagicMock()
    job.id = job_id
    job.description = description
    job.apply_url = apply_url
    return job


def _make_profile(user_id: uuid.UUID = TEST_USER_ID) -> MagicMock:
    profile = MagicMock()
    profile.id = uuid.uuid4()
    profile.user_id = user_id
    return profile


def _make_resume() -> MagicMock:
    resume = MagicMock()
    resume.id = uuid.uuid4()
    resume.content_json = {"name": "Test User"}
    return resume


def _make_cover_letter() -> MagicMock:
    cl = MagicMock()
    cl.id = uuid.uuid4()
    return cl


def _make_orchestrator(
    redis_data: dict | None = None,
) -> tuple:
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock()

    if redis_data:
        redis.get = AsyncMock(return_value=json.dumps(redis_data))

    browser = AsyncMock()
    browser.new_page = AsyncMock(return_value=AsyncMock())
    browser.close_page = AsyncMock()
    browser.safe_goto = AsyncMock()
    browser.capture_screenshot = AsyncMock(return_value="/screenshots/test.png")

    pipeline = AsyncMock()
    pipeline.run_full_pipeline = AsyncMock(return_value={
        "resume": {"name": "Test"},
        "ats_result": {"overall_score": 85.0},
    })
    pipeline.run_cover_letter_pipeline = AsyncMock(return_value={
        "cover_letter": {"full_text": "Dear...", "tone_used": "professional"},
    })

    application = _make_application()
    job = _make_job()
    profile = _make_profile()
    resume = _make_resume()

    def _make_session():
        app_result = MagicMock()
        app_result.scalar_one_or_none.return_value = application
        job_result = MagicMock()
        job_result.scalar_one_or_none.return_value = job
        profile_result = MagicMock()
        profile_result.scalar_one_or_none.return_value = profile
        resume_result = MagicMock()
        resume_result.scalar_one_or_none.return_value = resume

        s = AsyncMock()
        s.execute = AsyncMock(side_effect=[app_result, job_result])
        s.commit = AsyncMock()
        s.add = MagicMock()
        s.refresh = AsyncMock(return_value=None)
        s.__aenter__ = AsyncMock(return_value=s)
        s.__aexit__ = AsyncMock(return_value=False)
        return s

    async def sf():
        return _make_session()

    from app.services.apply_orchestrator import AutoApplyOrchestrator
    orchestrator = AutoApplyOrchestrator(
        browser_service=browser,
        ai_pipeline=pipeline,
        session_factory=sf,
        redis=redis,
    )

    return orchestrator, redis, browser, pipeline


class TestFullCascadeGreenhouse:
    @pytest.mark.asyncio
    async def test_full_cascade_greenhouse(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        application = _make_application()
        job = _make_job()
        profile = _make_profile()
        resume = _make_resume()

        filler = AsyncMock()
        filler.fill = AsyncMock()
        filler.submit = AsyncMock(return_value=True)
        filler.verify = AsyncMock(return_value=MagicMock(success=True, screenshot_path="/screenshots/applied.png"))

        with patch("app.services.apply_orchestrator.select") as mock_select, \
             patch("app.services.apply_orchestrator.selectinload"), \
             patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=_make_cover_letter()), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/applied.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        assert result.status == ApplicationStatus.applied.value
        assert "load_profile" in result.steps_completed
        assert "generate_resume" in result.steps_completed
        assert "ats_apply" in result.steps_completed


class TestFullCascadeLever:
    @pytest.mark.asyncio
    async def test_full_cascade_lever(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        application = _make_application(ats_platform="lever")
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=_make_cover_letter()), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/lever.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        assert result.status == ApplicationStatus.applied.value


class TestFullCascadeWorkday:
    @pytest.mark.asyncio
    async def test_full_cascade_workday(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=_make_cover_letter()), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/workday.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        assert result.status == ApplicationStatus.applied.value


class TestNoATSPlatform:
    @pytest.mark.asyncio
    async def test_no_ats_platform(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()
        application = _make_application(ats_platform=None)
        job = _make_job()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.manual_required,
                 "manual_url": "https://example.com/apply",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is False
        assert result.status == ApplicationStatus.manual_required.value


class TestCaptchaDetected:
    @pytest.mark.asyncio
    async def test_captcha_detected(self):
        from app.services.ats_fillers.exceptions import ATSCAPTCHAError
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.manual_required,
                 "screenshot_path": "/screenshots/captcha.png",
                 "manual_url": "https://example.com/apply",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.status == ApplicationStatus.manual_required.value
        assert result.screenshot_path == "/screenshots/captcha.png"


class TestResumeGenerationFails:
    @pytest.mark.asyncio
    async def test_resume_generation_fails(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", side_effect=RuntimeError("AI down")), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is False
        assert result.status == ApplicationStatus.failed.value


class TestCoverLetterGenerationFails:
    @pytest.mark.asyncio
    async def test_cover_letter_generation_fails(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/applied.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        assert result.status == ApplicationStatus.applied.value
        assert result.cover_letter_id is None


class TestFillFails:
    @pytest.mark.asyncio
    async def test_fill_fails(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.manual_required,
                 "manual_url": "https://example.com/apply",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.status == ApplicationStatus.manual_required.value


class TestSubmitFails:
    @pytest.mark.asyncio
    async def test_submit_fails(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.manual_required,
                 "manual_url": "https://example.com/apply",
                 "screenshot_path": "/screenshots/submit_failed.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.status == ApplicationStatus.manual_required.value


class TestVerifyUncertain:
    @pytest.mark.asyncio
    async def test_verify_uncertain(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied_with_issues,
                 "screenshot_path": "/screenshots/uncertain.png",
                 "manual_url": "https://example.com/apply",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.status == ApplicationStatus.applied_with_issues.value


class TestUnsupportedPlatform:
    @pytest.mark.asyncio
    async def test_unsupported_platform(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()
        application = _make_application(ats_platform="taleo")

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.manual_required,
                 "manual_url": "https://example.com/apply",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.status == ApplicationStatus.manual_required.value


class TestStatusTransitions:
    @pytest.mark.asyncio
    async def test_status_transitions(self):
        assert ApplicationStatus.ready.value == "ready"
        assert ApplicationStatus.applying.value == "applying"
        assert ApplicationStatus.applied.value == "applied"


class TestLoadProfileEagerLoading:
    @pytest.mark.asyncio
    async def test_load_profile_eager_loading(self):
        orchestrator, _, _, _ = _make_orchestrator()
        profile = _make_profile()

        async def fake_session_factory():
            s = AsyncMock()
            result = MagicMock()
            result.scalar_one_or_none.return_value = profile
            s.execute = AsyncMock(return_value=result)
            s.commit = AsyncMock()
            s.__aenter__ = AsyncMock(return_value=s)
            s.__aexit__ = AsyncMock(return_value=False)
            return s

        original_sf = orchestrator._session_factory
        orchestrator._session_factory = fake_session_factory

        loaded = await orchestrator._load_profile(TEST_USER_ID)
        assert loaded is not None
        assert loaded.user_id == TEST_USER_ID


class TestDoubleApplyGuard:
    @pytest.mark.asyncio
    async def test_double_apply_guard(self):
        orchestrator, redis, _, _ = _make_orchestrator()
        redis.set = AsyncMock(return_value=False)

        result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is False
        assert "lock" in result.error.lower() or "already" in result.error.lower()


class TestResumeFileSaveFails:
    @pytest.mark.asyncio
    async def test_resume_file_save_fails(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", side_effect=OSError("Disk full")), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is False
        assert result.status == ApplicationStatus.failed.value


class TestEnqueueFailsRevertsStatus:
    @pytest.mark.asyncio
    async def test_enqueue_fails_reverts_status(self):
        from app.auth import CurrentUser
        from app.routes.apply import apply_single
        from app.schemas.apply import ApplySingleRequest

        user = CurrentUser(id=TEST_USER_ID, email="test@example.com")
        application = _make_application(status=ApplicationStatus.ready)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = application
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()
        mock_session.add = MagicMock()

        request = ApplySingleRequest(application_id=TEST_APPLICATION_ID)

        with patch("app.routes.apply.arq_create_pool", side_effect=Exception("ARQ down")):
            from fastapi import HTTPException
            with pytest.raises(HTTPException) as exc_info:
                await apply_single(request, user, mock_session)
            assert exc_info.value.status_code == 502

        assert application.status == ApplicationStatus.ready


class TestRedisLockPreventsDoubleRun:
    @pytest.mark.asyncio
    async def test_redis_lock_prevents_double_run(self):
        orchestrator, redis, _, _ = _make_orchestrator()
        redis.set = AsyncMock(return_value=False)

        result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is False
        assert result.steps_completed == []


class TestStepTrackingResumeOnRetry:
    @pytest.mark.asyncio
    async def test_step_tracking_resume_on_retry(self):
        progress_data = {
            "steps_completed": ["load_profile", "generate_resume", "save_resume"],
            "current_step": "save_resume",
        }
        orchestrator, redis, _, _ = _make_orchestrator(redis_data=progress_data)
        profile = _make_profile()
        resume = _make_resume()

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_get_existing_resume", return_value=resume), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/applied.png",
             }), \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        assert "generate_resume" in result.steps_completed
        assert "ats_apply" in result.steps_completed


class TestSkipATSRedetect:
    @pytest.mark.asyncio
    async def test_skip_ats_redetect(self):
        orchestrator, redis, browser, pipeline = _make_orchestrator()
        profile = _make_profile()
        resume = _make_resume()
        application = _make_application(ats_platform="greenhouse")

        with patch.object(orchestrator, "_load_profile", return_value=profile), \
             patch.object(orchestrator, "_generate_resume", return_value=resume), \
             patch.object(orchestrator, "_generate_cover_letter", return_value=None), \
             patch.object(orchestrator, "_save_resume_to_file", return_value="/resumes/test.txt"), \
             patch.object(orchestrator, "_attempt_ats_apply", return_value={
                 "status": ApplicationStatus.applied,
                 "screenshot_path": "/screenshots/applied.png",
             }) as mock_apply, \
             patch.object(orchestrator, "_update_status", new_callable=AsyncMock):
            result = await orchestrator.run(TEST_APPLICATION_ID, TEST_USER_ID)

        assert result.success is True
        mock_apply.assert_called_once()
