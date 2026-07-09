"""Live-tail hub: fan out captured-request events to WebSocket clients.

Publish path (ADR-002): if Redis is available, publish to channel `bin:{id}` and
let the subscriber loop deliver to every instance's local sockets; without Redis,
deliver to local sockets directly (in-process fallback, used in tests).
"""

import json
import logging

from fastapi import WebSocket

from app.core.redis import get_redis

logger = logging.getLogger(__name__)

CHANNEL_PREFIX = "bin:"


class LiveHub:
    def __init__(self) -> None:
        self._local: dict[str, set[WebSocket]] = {}

    def register(self, bin_id: str, ws: WebSocket) -> None:
        """Add an already-accepted socket to the local fan-out set."""
        self._local.setdefault(bin_id, set()).add(ws)

    def disconnect(self, bin_id: str, ws: WebSocket) -> None:
        sockets = self._local.get(bin_id)
        if sockets:
            sockets.discard(ws)
            if not sockets:
                self._local.pop(bin_id, None)

    async def broadcast_local(self, bin_id: str, message: str) -> None:
        for ws in list(self._local.get(bin_id, set())):
            try:
                await ws.send_text(message)
            except Exception:  # noqa: BLE001 - drop dead sockets
                self.disconnect(bin_id, ws)

    async def publish(self, bin_id: str, event: dict) -> None:
        message = json.dumps(event, default=str)
        client = get_redis()
        if client is None:
            await self.broadcast_local(bin_id, message)
            return
        try:
            await client.publish(f"{CHANNEL_PREFIX}{bin_id}", message)
        except Exception as exc:  # noqa: BLE001
            logger.warning("live publish failed, delivering locally: %s", exc)
            await self.broadcast_local(bin_id, message)


hub = LiveHub()


async def redis_subscriber() -> None:
    """Background loop: forward Redis pub/sub messages to local sockets."""
    client = get_redis()
    if client is None:
        return
    pubsub = client.pubsub()
    await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    async for msg in pubsub.listen():
        if msg.get("type") != "pmessage":
            continue
        channel = msg["channel"]
        bin_id = channel.split(":", 1)[1]
        await hub.broadcast_local(bin_id, msg["data"])
