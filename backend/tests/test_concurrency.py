import uuid
from unittest.mock import AsyncMock

import pytest


APP_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())


@pytest.mark.asyncio
async def test_apply_single_job_skips_when_lock_held():
    """apply_single_job returns skipped/lock_held when Redis lock is already set."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1")
    ctx = {"redis": redis}

    from app.workers.apply_worker import apply_single_job
    result = await apply_single_job(ctx, APP_ID, USER_ID)

    assert result["status"] == "skipped"
    assert result["reason"] == "lock_held"

    lock_key = f"apply_lock:{APP_ID}"
    redis.get.assert_awaited_once_with(lock_key)
