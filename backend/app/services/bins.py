from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.ids import generate_bin_id
from app.models import Bin, CapturedRequest


async def create_bin(db: AsyncSession) -> Bin:
    now = datetime.now(UTC)
    bin_ = Bin(
        id=generate_bin_id(),
        expires_at=now + timedelta(days=settings.bin_ttl_days),
        request_count=0,
    )
    db.add(bin_)
    await db.commit()
    await db.refresh(bin_)
    return bin_


async def get_bin(db: AsyncSession, bin_id: str) -> Bin:
    bin_ = await db.get(Bin, bin_id)
    if bin_ is None or _is_expired(bin_):
        raise NotFoundError(f"Bin {bin_id} not found or expired")
    return bin_


async def delete_bin(db: AsyncSession, bin_id: str) -> None:
    bin_ = await get_bin(db, bin_id)
    await db.delete(bin_)
    await db.commit()


async def list_requests(
    db: AsyncSession, bin_id: str, *, limit: int = 50, before: int | None = None
) -> list[CapturedRequest]:
    stmt = select(CapturedRequest).where(CapturedRequest.bin_id == bin_id)
    if before is not None:
        stmt = stmt.where(CapturedRequest.id < before)
    stmt = stmt.order_by(CapturedRequest.id.desc()).limit(limit)
    return list((await db.execute(stmt)).scalars().all())


async def get_request(db: AsyncSession, bin_id: str, request_id: int) -> CapturedRequest:
    stmt = select(CapturedRequest).where(
        CapturedRequest.id == request_id, CapturedRequest.bin_id == bin_id
    )
    req = (await db.execute(stmt)).scalar_one_or_none()
    if req is None:
        raise NotFoundError(f"Request {request_id} not found")
    return req


async def cleanup_expired(db: AsyncSession) -> int:
    """Delete expired bins (their requests cascade). Returns count removed."""
    now = datetime.now(UTC)
    ids = (
        (await db.execute(select(Bin.id).where(Bin.expires_at < now))).scalars().all()
    )
    if not ids:
        return 0
    await db.execute(delete(Bin).where(Bin.id.in_(ids)))
    await db.commit()
    return len(ids)


def _is_expired(bin_: Bin) -> bool:
    expires = bin_.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return expires < datetime.now(UTC)


async def trim_and_count(db: AsyncSession, bin_id: str) -> int:
    """Ring-buffer: keep only the newest max_requests_per_bin rows."""
    total = await db.scalar(
        select(func.count()).select_from(CapturedRequest).where(
            CapturedRequest.bin_id == bin_id
        )
    )
    total = total or 0
    limit = settings.max_requests_per_bin
    if total > limit:
        old_ids = (
            await db.execute(
                select(CapturedRequest.id)
                .where(CapturedRequest.bin_id == bin_id)
                .order_by(CapturedRequest.id.asc())
                .limit(total - limit)
            )
        ).scalars().all()
        await db.execute(delete(CapturedRequest).where(CapturedRequest.id.in_(old_ids)))
        total = limit
    return total
