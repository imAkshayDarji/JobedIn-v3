from urllib.parse import unquote, urlparse

from arq.connections import RedisSettings  # noqa: F401 — re-export for route modules
from redis.asyncio import Redis

from app.config import settings

QUEUE_JOBS = "arq:queue:jobs"
QUEUE_AI = "arq:queue:ai"
QUEUE_APPLY = "arq:queue:apply"


def redis_settings_from_url(url: str) -> RedisSettings:
    """Parse redis:// or rediss:// URLs including credentials (e.g. Railway Redis)."""
    parsed = urlparse(url)
    host = parsed.hostname or "localhost"
    port = parsed.port or 6379
    path_remainder = parsed.path.lstrip("/")
    db = int(path_remainder) if path_remainder.isdigit() else 0
    username = unquote(parsed.username) if parsed.username else None
    password = unquote(parsed.password) if parsed.password else None
    ssl = parsed.scheme == "rediss"
    return RedisSettings(
        host=host,
        port=port,
        database=db,
        username=username,
        password=password,
        ssl=ssl,
    )

_redis: Redis | None = None


async def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
