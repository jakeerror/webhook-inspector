"""TTL / expiry behaviour (SPEC §1, ADR-004), tested at the service layer.

Self-contained file-based sqlite (NullPool) to avoid the in-memory StaticPool
cross-event-loop sharing used by the httpx client fixture.
"""

import tempfile
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import NotFoundError
from app.db.base import Base
from app.models import Bin
from app.services import bins as bins_svc

_engine = create_async_engine(f"sqlite+aiosqlite:///{tempfile.mktemp(suffix='.db')}")
_Session = async_sessionmaker(_engine, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _schema():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_valid_then_expired_bin():
    async with _Session() as db:
        bin_ = await bins_svc.create_bin(db)
        assert (await bins_svc.get_bin(db, bin_.id)).id == bin_.id  # valid → found

        bin_.expires_at = datetime.now(UTC) - timedelta(days=1)
        await db.commit()
        with pytest.raises(NotFoundError):
            await bins_svc.get_bin(db, bin_.id)  # expired → not found


async def test_cleanup_removes_expired_bins():
    async with _Session() as db:
        bin_ = await bins_svc.create_bin(db)
        bin_.expires_at = datetime.now(UTC) - timedelta(days=1)
        await db.commit()

        removed = await bins_svc.cleanup_expired(db)
        assert removed >= 1
        assert await db.get(Bin, bin_.id) is None
