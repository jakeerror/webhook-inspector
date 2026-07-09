from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.base import Base, BigIntPK, TimestampMixin

if TYPE_CHECKING:
    from app.models.bin import Bin

# JSONB on Postgres, generic JSON on sqlite (tests).
JsonType = JSONB().with_variant(JSON(), "sqlite")


class CapturedRequest(Base, TimestampMixin):
    __tablename__ = "captured_requests"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True)
    bin_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("bins.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    query: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    headers: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    content_type: Mapped[str | None] = mapped_column(String(255), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_ip: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    bin: Mapped[Bin] = relationship(back_populates="requests")
