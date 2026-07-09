"""Async Redis client with graceful degradation.

When DISABLE_REDIS=true (tests) or on connection error, callers fall back to
in-process behaviour: no pub/sub fan-out across instances, rate limits allow.
"""

import logging
from functools import lru_cache

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


@lru_cache
def get_redis() -> aioredis.Redis | None:
    import os

    if os.getenv("DISABLE_REDIS") == "true":
        return None
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=2,
    )


async def publish(channel: str, message: str) -> None:
    client = get_redis()
    if client is None:
        return
    try:
        await client.publish(channel, message)
    except Exception as exc:  # noqa: BLE001 - best-effort fan-out
        logger.warning("redis publish failed: %s", exc)


async def incr_with_expire(key: str, window_seconds: int) -> int | None:
    """Rate-limit counter; returns None if Redis is unavailable (fail-open)."""
    client = get_redis()
    if client is None:
        return None
    try:
        count = await client.incr(key)
        if count == 1:
            await client.expire(key, window_seconds)
        return count
    except Exception as exc:  # noqa: BLE001
        logger.warning("redis incr failed: %s", exc)
        return None


async def ping() -> bool:
    client = get_redis()
    if client is None:
        return False
    try:
        return await client.ping()
    except Exception:  # noqa: BLE001
        return False
