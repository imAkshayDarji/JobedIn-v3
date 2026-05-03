import importlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_redis_module():
    """Reset module-level _redis before and after each test."""
    import app.services.redis_pool as redis_mod
    redis_mod._redis = None
    yield
    redis_mod._redis = None


async def test_get_redis_creates_new_instance():
    mock_redis_instance = AsyncMock()

    with patch("app.services.redis_pool.Redis") as MockRedis:
        MockRedis.from_url.return_value = mock_redis_instance
        import app.services.redis_pool as redis_mod

        result = await redis_mod.get_redis()

    MockRedis.from_url.assert_called_once()
    assert result is mock_redis_instance


async def test_get_redis_returns_same_instance():
    mock_redis_instance = AsyncMock()

    with patch("app.services.redis_pool.Redis") as MockRedis:
        MockRedis.from_url.return_value = mock_redis_instance
        import app.services.redis_pool as redis_mod

        first = await redis_mod.get_redis()
        second = await redis_mod.get_redis()

    assert first is second
    assert MockRedis.from_url.call_count == 1


async def test_close_redis_closes_connection():
    mock_redis_instance = AsyncMock()

    with patch("app.services.redis_pool.Redis") as MockRedis:
        MockRedis.from_url.return_value = mock_redis_instance
        import app.services.redis_pool as redis_mod

        await redis_mod.get_redis()
        assert redis_mod._redis is not None

        await redis_mod.close_redis()

    mock_redis_instance.aclose.assert_awaited_once()
    assert redis_mod._redis is None


async def test_close_redis_when_none():
    import app.services.redis_pool as redis_mod

    assert redis_mod._redis is None
    await redis_mod.close_redis()
    assert redis_mod._redis is None
