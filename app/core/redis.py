import json
from collections.abc import AsyncGenerator
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

settings = get_settings()

_redis_pool: aioredis.Redis | None = None


def get_redis_pool() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    redis = get_redis_pool()
    yield redis


# ── Helpers ────────────────────────────────────────────

async def redis_set(
    redis: aioredis.Redis,
    key: str,
    value: Any,
    ttl_seconds: int = 3600,
) -> None:
    await redis.setex(key, ttl_seconds, json.dumps(value))


async def redis_get(redis: aioredis.Redis, key: str) -> Any | None:
    raw = await redis.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def redis_delete(redis: aioredis.Redis, key: str) -> None:
    await redis.delete(key)