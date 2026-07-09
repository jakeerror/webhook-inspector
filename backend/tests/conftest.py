import os

os.environ.setdefault("DISABLE_REDIS", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("MAX_REQUESTS_PER_BIN", "5")  # small, for ring-buffer test

from collections.abc import AsyncGenerator  # noqa: E402

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

test_engine = create_async_engine(
    "sqlite+aiosqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = async_sessionmaker(test_engine, expire_on_commit=False, autoflush=False)


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async def _get_db():
        async with TestSession() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
def create_bin(client: AsyncClient):
    """Factory fixture: create a fresh bin and return its JSON."""

    async def _create() -> dict:
        resp = await client.post("/api/v1/bins")
        assert resp.status_code == 201, resp.text
        return resp.json()

    return _create
