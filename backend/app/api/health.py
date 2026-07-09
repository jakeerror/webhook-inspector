from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core import redis as redis_module

router = APIRouter(tags=["service"])


@router.get("/health")
async def health(db: SessionDep) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    if redis_module.get_redis() is None:
        redis_status = "disabled"
    else:
        redis_status = "ok" if await redis_module.ping() else "down"
    return {
        "status": "degraded" if redis_status == "down" else "ok",
        "db": "ok",
        "redis": redis_status,
    }
