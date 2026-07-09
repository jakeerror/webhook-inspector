"""WebSocket live-tail integration test via Starlette TestClient.

Uses a dedicated file-based sqlite engine (NullPool → no cross-event-loop
connection sharing, unlike the in-memory StaticPool used by the async tests).
"""

import asyncio
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.session import get_db
from app.main import app

_DB_FILE = tempfile.mktemp(suffix=".db")
_engine = create_async_engine(f"sqlite+aiosqlite:///{_DB_FILE}")
_Session = async_sessionmaker(_engine, expire_on_commit=False)


async def _init_schema() -> None:
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def ws_client():
    asyncio.run(_init_schema())

    async def _get_db():
        async with _Session() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_websocket_streams_captured_request(ws_client):
    bin_ = ws_client.post("/api/v1/bins").json()
    bid = bin_["id"]

    with ws_client.websocket_connect(f"/ws/bins/{bid}") as ws:
        assert ws.receive_json() == {"type": "connected", "bin_id": bid}

        # Capturing a request must push a live event over the socket.
        ws_client.post(f"/in/{bid}/hook?x=1", json={"hello": "world"})
        event = ws.receive_json()
        assert event["type"] == "request"
        assert event["data"]["method"] == "POST"
        assert event["data"]["path"] == "hook"


def test_websocket_rejects_unknown_bin(ws_client):
    # Starlette raises when the server closes the socket (code 4404).
    with pytest.raises(Exception), ws_client.websocket_connect("/ws/bins/nope") as ws:  # noqa: B017
        ws.receive_json()
