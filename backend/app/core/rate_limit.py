"""Redis-backed rate limiting as a FastAPI dependency (SPEC §7, fail-open)."""

from collections.abc import Awaitable, Callable

from fastapi import HTTPException, Request, status

from app.core.redis import incr_with_expire


def rate_limiter(
    scope: str, limit: int, window_seconds: int = 60
) -> Callable[[Request], Awaitable[None]]:
    async def _dependency(request: Request) -> None:
        client_ip = request.client.host if request.client else "anonymous"
        key = f"rl:{scope}:{client_ip}"
        count = await incr_with_expire(key, window_seconds)
        if count is not None and count > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
            )

    return _dependency
