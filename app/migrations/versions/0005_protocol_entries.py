"""Protocol journal rows on the participant. No catalog id.

Revision ID: 0005_protocol_entries
Revises: 0004_login_sessions
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_protocol_entries"
down_revision: str | None = "0004_login_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add journal rows. Deleting a participant removes them."""
    op.create_table(
        "protocol_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("dose", sa.String(length=80), nullable=True),
        sa.Column("started_on", sa.Date(), nullable=False),
        sa.Column("ended_on", sa.Date(), nullable=True),
        sa.Column("note", sa.String(length=2000), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "kind IN ('drug', 'supplement', 'nutrition', 'activity', 'sleep', 'other')",
            name="ck_protocol_entries_kind",
        ),
        sa.CheckConstraint(
            "ended_on IS NULL OR ended_on >= started_on",
            name="ck_protocol_entries_period",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_protocol_entries_user_id", "protocol_entries", ["user_id"])


def downgrade() -> None:
    """Remove journal rows."""
    op.drop_index("ix_protocol_entries_user_id", table_name="protocol_entries")
    op.drop_table("protocol_entries")
