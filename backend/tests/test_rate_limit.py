"""Rate limiter tests (SPEC §7). Uses fakeredis to exercise the 429 path that
the default DISABLE_REDIS=true (fail-open) config skips."""

import fakeredis.aioredis
import pytest
from fastapi import HTTPException

from app.core import redis as redis_mod
from app.core.rate_limit import rate_limiter


class _Req:
    def __init__(self, ip: str) -> None:
        self.client = type("C", (), {"host": ip})()


async def test_allows_within_limit_then_blocks(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_mod, "get_redis", lambda: fake)

    guard = rate_limiter("test", limit=2, window_seconds=60)
    req = _Req("1.2.3.4")

    await guard(req)  # 1 — ok
    await guard(req)  # 2 — ok
    with pytest.raises(HTTPException) as exc:
        await guard(req)  # 3 — blocked
    assert exc.value.status_code == 429


async def test_limit_is_per_ip(monkeypatch):
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    monkeypatch.setattr(redis_mod, "get_redis", lambda: fake)

    guard = rate_limiter("test", limit=1, window_seconds=60)
    await guard(_Req("1.1.1.1"))  # ok
    await guard(_Req("2.2.2.2"))  # different IP → ok
    with pytest.raises(HTTPException):
        await guard(_Req("1.1.1.1"))  # same IP again → blocked


async def test_fails_open_without_redis(monkeypatch):
    monkeypatch.setattr(redis_mod, "get_redis", lambda: None)
    guard = rate_limiter("test", limit=1, window_seconds=60)
    # Never raises when Redis is unavailable.
    for _ in range(5):
        await guard(_Req("1.2.3.4"))
