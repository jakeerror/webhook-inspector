import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import bins, health, ingest, ws
from app.core.config import settings
from app.core.errors import DomainError
from app.db.session import AsyncSessionLocal
from app.services import bins as bins_svc
from app.services.live import redis_subscriber

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    tasks = [
        asyncio.create_task(redis_subscriber()),  # no-op if Redis disabled
        asyncio.create_task(_cleanup_loop()),
    ]
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()


async def _cleanup_loop() -> None:
    """Periodically delete expired bins (SPEC §1, ADR-004)."""
    while True:
        await asyncio.sleep(settings.cleanup_interval_seconds)
        try:
            async with AsyncSessionLocal() as db:
                removed = await bins_svc.cleanup_expired(db)
                if removed:
                    logger.info("cleanup: removed %d expired bins", removed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("cleanup loop error: %s", exc)


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(DomainError)
    async def _domain_error(_: Request, exc: DomainError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(ws.router)
    app.include_router(bins.router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
