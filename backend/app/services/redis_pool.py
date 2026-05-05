from arq.connections import RedisSettings  # noqa: F401 — re-export for route modules
from redis.asyncio import Redis

from app.config import settings

QUEUE_JOBS = "arq:queue:jobs"
QUEUE_AI = "arq:queue:ai"
QUEUE_APPLY = "arq:queue:apply"


def redis_settings_from_url(url: str) -> RedisSettings:
    stripped = url.replace("redis://", "")
    parts = stripped.split("/")
    db = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0
    host_port = parts[0].split(":")
    host = host_port[0] if host_port[0] else "localhost"
    port = int(host_port[1]) if len(host_port) > 1 else 6379
    return RedisSettings(host=host, port=port, database=db)

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
