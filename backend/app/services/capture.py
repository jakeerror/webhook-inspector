from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import Bin, CapturedRequest
from app.schemas.request import CapturedRequestSummary
from app.services import bins as bins_service
from app.services.live import hub


async def capture(
    db: AsyncSession, bin_: Bin, request: Request, path: str
) -> CapturedRequest:
    raw = await request.body()
    size = len(raw)
    truncated = size > settings.max_body_bytes
    body_bytes = raw[: settings.max_body_bytes] if truncated else raw
    body = body_bytes.decode("utf-8", errors="replace")

    record = CapturedRequest(
        bin_id=bin_.id,
        method=request.method,
        path=path or "",
        query=dict(request.query_params),
        headers=dict(request.headers),
        content_type=request.headers.get("content-type"),
        body=body,
        body_truncated=truncated,
        source_ip=request.client.host if request.client else "",
        size_bytes=size,
    )
    db.add(record)
    await db.flush()  # assign id

    bin_.request_count = await bins_service.trim_and_count(db, bin_.id)
    await db.commit()
    await db.refresh(record)

    # Live fan-out (best-effort; never blocks capture).
    summary = CapturedRequestSummary.model_validate(record)
    await hub.publish(bin_.id, {"type": "request", "data": summary.model_dump(mode="json")})
    return record
