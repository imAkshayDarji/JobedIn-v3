import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


BULK_TASK_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_bulk_mixed_results():
    """apply_bulk_job processes mixed success/failure/manual_required results."""
    redis = AsyncMock()
    ctx = {"redis": redis}

    app_ids = [str(uuid.uuid4()) for _ in range(3)]

    results = [
        {"status": "applied", "application_id": app_ids[0]},
        {"status": "failed", "error": "Browser crash", "application_id": app_ids[1]},
        {"status": "manual_required", "application_id": app_ids[2]},
    ]

    with patch("app.workers.apply_worker.apply_single_job", new_callable=AsyncMock) as mock_single:
        mock_single.side_effect = results

        from app.workers.apply_worker import apply_bulk_job
        result = await apply_bulk_job(ctx, app_ids, str(uuid.uuid4()), BULK_TASK_ID)

    assert result["total"] == 3
    assert mock_single.call_count == 3


@pytest.mark.asyncio
async def test_update_bulk_progress_missing_redis_key():
    """_update_bulk_progress returns gracefully when Redis key is missing."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)

    from app.workers.apply_worker import _update_bulk_progress
    await _update_bulk_progress(redis, BULK_TASK_ID, {"status": "applied", "application_id": str(uuid.uuid4())})

    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_bulk_progress_corrupted_json():
    """_update_bulk_progress returns gracefully when stored data is not valid JSON."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"not valid json {{{")

    from app.workers.apply_worker import _update_bulk_progress
    await _update_bulk_progress(redis, BULK_TASK_ID, {"status": "applied", "application_id": str(uuid.uuid4())})

    redis.set.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_bulk_progress_manual_required_increments():
    """_update_bulk_progress increments manual_required counter for manual_required status."""
    redis = AsyncMock()
    existing_data = json.dumps({
        "total": 2,
        "completed": 0,
        "failed": 0,
        "manual_required": 0,
        "pending": 2,
        "results": [],
    })
    redis.get = AsyncMock(return_value=existing_data)

    from app.workers.apply_worker import _update_bulk_progress
    await _update_bulk_progress(redis, BULK_TASK_ID, {"status": "manual_required", "application_id": str(uuid.uuid4())})

    set_call = redis.set.call_args
    updated = json.loads(set_call[0][1])
    assert updated["manual_required"] == 1
    assert updated["pending"] == 1
    assert updated["completed"] == 0
    assert updated["failed"] == 0


@pytest.mark.asyncio
async def test_apply_bulk_job_continues_on_individual_failure():
    """apply_bulk_job catches individual exceptions and continues processing remaining jobs."""
    redis = AsyncMock()
    ctx = {"redis": redis}

    app_ids = [str(uuid.uuid4()) for _ in range(3)]

    call_count = 0

    async def _mock_single(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Worker crashed mid-apply")
        return {"status": "applied", "application_id": args[1]}

    with patch("app.workers.apply_worker.apply_single_job", new_callable=AsyncMock) as mock_single:
        mock_single.side_effect = _mock_single

        from app.workers.apply_worker import apply_bulk_job
        result = await apply_bulk_job(ctx, app_ids, str(uuid.uuid4()), BULK_TASK_ID)

    assert mock_single.call_count == 3
    assert result["total"] == 3
