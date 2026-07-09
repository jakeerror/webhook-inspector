from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import SessionDep
from app.core.config import settings
from app.core.rate_limit import rate_limiter
from app.schemas.bin import BinCreateResponse, BinRead
from app.schemas.request import (
    CapturedRequestRead,
    CapturedRequestSummary,
    ReplayRequest,
    ReplayResponse,
)
from app.services import bins as svc
from app.services import replay as replay_svc

router = APIRouter(prefix="/bins", tags=["bins"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(rate_limiter("create_bin", settings.rate_limit_create_bin_per_min))
    ],
)
async def create_bin(db: SessionDep) -> BinCreateResponse:
    bin_ = await svc.create_bin(db)
    return BinCreateResponse(
        id=bin_.id,
        created_at=bin_.created_at,
        expires_at=bin_.expires_at,
        request_count=bin_.request_count,
        url=f"{settings.public_base_url}/in/{bin_.id}",
    )


# Returns an ORM object; the public schema differs, so use response_model.
@router.get("/{bin_id}", response_model=BinRead)
async def get_bin(bin_id: str, db: SessionDep):
    return await svc.get_bin(db, bin_id)


@router.delete("/{bin_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bin(bin_id: str, db: SessionDep) -> None:
    await svc.delete_bin(db, bin_id)


@router.get("/{bin_id}/requests", response_model=list[CapturedRequestSummary])
async def list_requests(
    bin_id: str,
    db: SessionDep,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    before: int | None = None,
):
    await svc.get_bin(db, bin_id)  # 404 if missing/expired
    return await svc.list_requests(db, bin_id, limit=limit, before=before)


@router.get("/{bin_id}/requests/{request_id}", response_model=CapturedRequestRead)
async def get_request(bin_id: str, request_id: int, db: SessionDep):
    await svc.get_bin(db, bin_id)
    return await svc.get_request(db, bin_id, request_id)


@router.post("/{bin_id}/requests/{request_id}/replay")
async def replay_request(
    bin_id: str, request_id: int, payload: ReplayRequest, db: SessionDep
) -> ReplayResponse:
    await svc.get_bin(db, bin_id)
    return await replay_svc.replay(db, bin_id, request_id, payload.target_url)
