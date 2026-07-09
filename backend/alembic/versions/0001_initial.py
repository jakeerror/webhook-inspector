"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-06
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "bins",
        sa.Column("id", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id", name="pk_bins"),
    )
    op.create_index("ix_bins_expires_at", "bins", ["expires_at"])

    op.create_table(
        "captured_requests",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bin_id", sa.String(16), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(1024), nullable=False, server_default=""),
        sa.Column("query", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("headers", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("content_type", sa.String(255), nullable=True),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("body_truncated", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("source_ip", sa.String(64), nullable=False, server_default=""),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["bin_id"],
            ["bins.id"],
            name="fk_captured_requests_bin_id_bins",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_captured_requests"),
    )
    op.create_index(
        "ix_captured_requests_bin_id", "captured_requests", ["bin_id"]
    )


def downgrade() -> None:
    op.drop_table("captured_requests")
    op.drop_table("bins")
