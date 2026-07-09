"""Live-tail hub unit tests (ADR-002). No Redis → in-process fan-out."""

from app.services.live import LiveHub


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[str] = []

    async def send_text(self, message: str) -> None:
        self.sent.append(message)


async def test_broadcast_local_delivers_to_registered_sockets():
    hub = LiveHub()
    ws1, ws2 = FakeWS(), FakeWS()
    hub.register("bin1", ws1)  # type: ignore[arg-type]
    hub.register("bin1", ws2)  # type: ignore[arg-type]
    hub.register("bin2", FakeWS())  # type: ignore[arg-type]

    await hub.broadcast_local("bin1", "hello")
    assert ws1.sent == ["hello"]
    assert ws2.sent == ["hello"]


async def test_publish_without_redis_delivers_locally():
    hub = LiveHub()
    ws = FakeWS()
    hub.register("bin1", ws)  # type: ignore[arg-type]

    await hub.publish("bin1", {"type": "request", "data": {"id": 1}})
    assert len(ws.sent) == 1
    assert '"type": "request"' in ws.sent[0]


async def test_disconnect_removes_socket():
    hub = LiveHub()
    ws = FakeWS()
    hub.register("bin1", ws)  # type: ignore[arg-type]
    hub.disconnect("bin1", ws)  # type: ignore[arg-type]

    await hub.broadcast_local("bin1", "hello")
    assert ws.sent == []
