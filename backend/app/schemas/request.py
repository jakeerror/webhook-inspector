from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CapturedRequestSummary(BaseModel):
    """Lightweight shape used in lists and WebSocket events."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    method: str
    path: str
    content_type: str | None
    size_bytes: int
    created_at: datetime


class CapturedRequestRead(CapturedRequestSummary):
    bin_id: str
    query: dict[str, Any]
    headers: dict[str, Any]
    body: str
    body_truncated: bool
    source_ip: str


class ReplayRequest(BaseModel):
    target_url: str


class ReplayResponse(BaseModel):
    status: int
    duration_ms: int
