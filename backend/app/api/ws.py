from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.deps import SessionDep
from app.core.errors import NotFoundError
from app.services import bins as bins_svc
from app.services.live import hub

router = APIRouter()


@router.websocket("/ws/bins/{bin_id}")
async def ws_bin(websocket: WebSocket, bin_id: str, db: SessionDep) -> None:
    await websocket.accept()

    try:
        await bins_svc.get_bin(db, bin_id)
    except NotFoundError:
        await websocket.close(code=4404, reason="bin not found or expired")
        return

    hub.register(bin_id, websocket)
    await websocket.send_json({"type": "connected", "bin_id": bin_id})
    try:
        while True:
            # We don't expect client messages; this keeps the socket open.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(bin_id, websocket)
