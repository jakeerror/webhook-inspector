import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import BadGatewayError
from app.core.ssrf import assert_safe_url
from app.schemas.request import ReplayResponse
from app.services import bins as bins_service

# Hop-by-hop / routing headers we must not forward to the replay target.
_STRIP_HEADERS = {
    "host",
    "content-length",
    "connection",
    "keep-alive",
    "transfer-encoding",
    "upgrade",
    "accept-encoding",
}


async def replay(
    db: AsyncSession, bin_id: str, request_id: int, target_url: str
) -> ReplayResponse:
    record = await bins_service.get_request(db, bin_id, request_id)

    assert_safe_url(target_url)  # raises ForbiddenError (403) if blocked

    headers = {
        k: v for k, v in record.headers.items() if k.lower() not in _STRIP_HEADERS
    }
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,  # a redirect could point back to a private host
            timeout=settings.replay_timeout_seconds,
        ) as client:
            response = await client.request(
                record.method,
                target_url,
                headers=headers,
                content=record.body.encode("utf-8"),
            )
    except httpx.HTTPError as exc:
        raise BadGatewayError(f"Replay target unreachable: {exc}") from exc

    duration_ms = int((time.perf_counter() - started) * 1000)
    return ReplayResponse(status=response.status_code, duration_ms=duration_ms)
