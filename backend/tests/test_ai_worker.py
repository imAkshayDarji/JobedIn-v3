import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


RESUME_ID = str(uuid.uuid4())
COVER_LETTER_ID = str(uuid.uuid4())
PREP_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
CANDIDATE_PROFILE_ID = str(uuid.uuid4())
JOB_DESCRIPTION = "Senior Python Developer at Acme Corp"


def _make_mock_resume(status="pending"):
    resume = MagicMock()
    resume.id = RESUME_ID
    resume.status = status
    resume.content_json = None
    resume.ats_score = None
    resume.ats_breakdown = None
    return resume


def _make_mock_cover_letter(status="pending"):
    cl = MagicMock()
    cl.id = COVER_LETTER_ID
    cl.status = status
    cl.content_json = None
    cl.content = None
    cl.tone = None
    cl.ai_model_used = None
    return cl


def _make_mock_prep(status="pending"):
    prep = MagicMock()
    prep.id = PREP_ID
    prep.status = status
    prep.questions = None
    return prep


class _AsyncSessionMock:
    """Mimics async_sessionmaker: callable returns an async context manager yielding the session."""

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return _AsyncCtxMgr(self._session)


class _AsyncCtxMgr:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        pass


def _make_mock_session(query_results: list):
    session = AsyncMock()
    results = []
    for val in query_results:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = val
        results.append(mock_result)
    session.execute.side_effect = results
    return session


def _make_pipeline_result(**overrides):
    result = {
        "resume": {"sections": [{"type": "summary", "content": "Experienced dev"}]},
        "ats_result": {"overall_score": 85, "breakdown": {}},
        "token_usage": {"calls": 1},
    }
    result.update(overrides)
    return result


def _make_cover_letter_pipeline_result(**overrides):
    result = {
        "cover_letter": {"full_text": "Dear Hiring Manager...", "tone_used": "professional"},
        "token_usage": {"calls": 1, "models_used": ["gpt-4"]},
    }
    result.update(overrides)
    return result


def _make_interview_pipeline_result(**overrides):
    result = {
        "questions": [{"q": "Tell me about yourself", "a": "I am a dev"}],
        "token_usage": {"calls": 1},
    }
    result.update(overrides)
    return result


@pytest.mark.asyncio
async def test_generate_resume_job_success():
    resume = _make_mock_resume()
    session = _make_mock_session([resume, resume, resume])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_full_pipeline = AsyncMock(return_value=_make_pipeline_result())
    mock_pipeline._token_usage = [
        {
            "task": "resume_generation",
            "model_used": "gpt-4",
            "prompt_tokens": 100,
            "completion_tokens": 200,
            "total_tokens": 300,
            "latency_ms": 1500,
        }
    ]

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_resume_job
        result = await generate_resume_job(
            ctx={},
            resume_id=RESUME_ID,
            user_id=USER_ID,
            candidate_profile_id=CANDIDATE_PROFILE_ID,
            job_description=JOB_DESCRIPTION,
        )

    assert resume.status == "completed"
    assert resume.content_json is not None
    assert resume.ats_score == 85


@pytest.mark.asyncio
async def test_generate_resume_job_pipeline_failure():
    resume = _make_mock_resume()
    session = _make_mock_session([resume, resume])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_full_pipeline = AsyncMock(side_effect=Exception("AI failed"))

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_resume_job
        with pytest.raises(Exception, match="AI failed"):
            await generate_resume_job(
                ctx={},
                resume_id=RESUME_ID,
                user_id=USER_ID,
                candidate_profile_id=CANDIDATE_PROFILE_ID,
                job_description=JOB_DESCRIPTION,
            )

    assert resume.status == "failed"


@pytest.mark.asyncio
async def test_generate_resume_job_resume_not_found():
    session = _make_mock_session([None])
    session_factory = _AsyncSessionMock(session)

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.ai_worker import generate_resume_job
        result = await generate_resume_job(
            ctx={},
            resume_id=RESUME_ID,
            user_id=USER_ID,
            candidate_profile_id=CANDIDATE_PROFILE_ID,
            job_description=JOB_DESCRIPTION,
        )

    assert result["status"] == "error"
    assert "not found" in result["error"].lower()


@pytest.mark.asyncio
async def test_generate_cover_letter_job_success():
    cover_letter = _make_mock_cover_letter()
    session = _make_mock_session([cover_letter, cover_letter, cover_letter])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_cover_letter_pipeline = AsyncMock(
        return_value=_make_cover_letter_pipeline_result()
    )
    mock_pipeline._token_usage = [
        {
            "task": "cover_letter",
            "model_used": "gpt-4",
            "prompt_tokens": 50,
            "completion_tokens": 150,
            "total_tokens": 200,
            "latency_ms": 800,
        }
    ]

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_cover_letter_job
        result = await generate_cover_letter_job(
            ctx={},
            cover_letter_id=COVER_LETTER_ID,
            user_id=USER_ID,
            candidate_profile_id=CANDIDATE_PROFILE_ID,
            job_description=JOB_DESCRIPTION,
            tone="professional",
        )

    assert cover_letter.status == "completed"
    assert cover_letter.content == "Dear Hiring Manager..."
    assert cover_letter.ai_model_used == "gpt-4"


@pytest.mark.asyncio
async def test_generate_cover_letter_job_failure():
    cover_letter = _make_mock_cover_letter()
    session = _make_mock_session([cover_letter, cover_letter])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_cover_letter_pipeline = AsyncMock(side_effect=Exception("AI failed"))

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_cover_letter_job
        with pytest.raises(Exception, match="AI failed"):
            await generate_cover_letter_job(
                ctx={},
                cover_letter_id=COVER_LETTER_ID,
                user_id=USER_ID,
                candidate_profile_id=CANDIDATE_PROFILE_ID,
                job_description=JOB_DESCRIPTION,
            )

    assert cover_letter.status == "failed"


@pytest.mark.asyncio
async def test_generate_interview_prep_job_success():
    prep = _make_mock_prep()
    session = _make_mock_session([prep, prep, prep])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_interview_prep_pipeline = AsyncMock(
        return_value=_make_interview_pipeline_result()
    )
    mock_pipeline._token_usage = [
        {
            "task": "interview_prep",
            "model_used": "gpt-4",
            "prompt_tokens": 80,
            "completion_tokens": 300,
            "total_tokens": 380,
            "latency_ms": 2000,
        }
    ]

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_interview_prep_job
        result = await generate_interview_prep_job(
            ctx={},
            prep_id=PREP_ID,
            user_id=USER_ID,
            candidate_profile_id=CANDIDATE_PROFILE_ID,
            job_description=JOB_DESCRIPTION,
        )

    assert prep.status == "completed"
    assert len(prep.questions) == 1


@pytest.mark.asyncio
async def test_generate_interview_prep_job_failure():
    prep = _make_mock_prep()
    session = _make_mock_session([prep, prep])
    session_factory = _AsyncSessionMock(session)

    mock_pipeline = MagicMock()
    mock_pipeline.run_interview_prep_pipeline = AsyncMock(side_effect=Exception("AI failed"))

    with patch("app.database.async_session_factory", session_factory), \
         patch("app.services.ai_pipeline.AIPipeline", return_value=mock_pipeline), \
         patch("app.services.ai_client.AIClient", return_value=MagicMock()):

        from app.workers.ai_worker import generate_interview_prep_job
        with pytest.raises(Exception, match="AI failed"):
            await generate_interview_prep_job(
                ctx={},
                prep_id=PREP_ID,
                user_id=USER_ID,
                candidate_profile_id=CANDIDATE_PROFILE_ID,
                job_description=JOB_DESCRIPTION,
            )

    assert prep.status == "failed"


@pytest.mark.asyncio
async def test_sweep_stale_jobs_completes_hscan_and_runs_db_sweep():
    """HSCAN terminates when cursor returns 0; DB stale-status update runs."""
    redis = AsyncMock()
    redis.hscan = AsyncMock(return_value=(0, {}))
    redis.hget = AsyncMock(return_value=None)

    session = AsyncMock()
    exec_result = MagicMock()
    scalars_result = MagicMock()
    scalars_result.all.return_value = []
    exec_result.scalars.return_value = scalars_result
    session.execute = AsyncMock(return_value=exec_result)
    session.commit = AsyncMock()

    session_factory = _AsyncSessionMock(session)
    ctx = {"redis": redis}

    with patch("app.database.async_session_factory", session_factory):
        from app.workers.ai_worker import sweep_stale_jobs

        await sweep_stale_jobs(ctx)

    redis.hscan.assert_awaited_once()
    assert session.execute.await_count == 3
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_persist_token_usage_creates_records():
    session = AsyncMock()

    usage_data = {
        "detail": [
            {
                "task": "resume_generation",
                "model_used": "gpt-4",
                "prompt_tokens": 100,
                "completion_tokens": 200,
                "total_tokens": 300,
                "latency_ms": 1500,
            },
            {
                "task": "ats_analysis",
                "model_used": "gpt-4",
                "prompt_tokens": 50,
                "completion_tokens": 100,
                "total_tokens": 150,
                "latency_ms": 500,
            },
        ]
    }

    with patch("app.models.ai_usage.AITokenUsage") as MockAITokenUsage:
        from app.workers.ai_worker import _persist_token_usage
        await _persist_token_usage(session, USER_ID, usage_data)

    assert session.add.call_count == 2
