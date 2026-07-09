from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.captured_request import CapturedRequest


class Bin(Base, TimestampMixin):
    __tablename__ = "bins"

    # URL-safe random slug; knowledge of the id grants access (ADR-001).
    id: Mapped[str] = mapped_column(String(16), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    request_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    requests: Mapped[list[CapturedRequest]] = relationship(
        back_populates="bin", cascade="all, delete-orphan", passive_deletes=True
    )
