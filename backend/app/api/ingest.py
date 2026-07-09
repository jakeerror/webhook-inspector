from fastapi import APIRouter, Depends, Request

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.services import bins as bins_svc
from app.services import capture as capture_svc

# Ingest is rate-limited at the router level (shared dependency).
router = APIRouter(
    tags=["ingest"],
    dependencies=[Depends(rate_limiter("ingest", settings.rate_limit_ingest_per_min))],
)

_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


async def _ingest(bin_id: str, path: str, request: Request, db: SessionDep) -> dict:
    bin_ = await bins_svc.get_bin(db, bin_id)  # 404 if missing/expired
    record = await capture_svc.capture(db, bin_, request, path)
    return {"ok": True, "request_id": record.id}


@router.api_route("/in/{bin_id}", methods=_METHODS)
async def ingest_root(bin_id: str, request: Request, db: SessionDep) -> dict:
    return await _ingest(bin_id, "", request, db)


@router.api_route("/in/{bin_id}/{path:path}", methods=_METHODS)
async def ingest_path(bin_id: str, path: str, request: Request, db: SessionDep) -> dict:
    return await _ingest(bin_id, path, request, db)
