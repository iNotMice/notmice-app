"""Separate credentials, one-time auth tokens, and consents from the participant row.

Revision ID: 0003_account_credentials
Revises: 0002_biomarker_reference
Create Date: 2026-09-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_account_credentials"
down_revision: str | None = "0002_biomarker_reference"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add identity tables and let a deleted participant take their provenance with them."""
    op.drop_constraint("provenance_entered_by_user_id_fkey", "provenance", type_="foreignkey")
    op.create_foreign_key(
        "provenance_entered_by_user_id_fkey",
        "provenance",
        "users",
        ["entered_by_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_table(
        "credentials",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("email_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "auth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("credential_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        sa.Column("token_sha256", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('confirm_email', 'reset_password')",
            name="ck_auth_tokens_purpose",
        ),
        sa.ForeignKeyConstraint(["credential_id"], ["credentials.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_sha256"),
    )
    op.create_index("ix_auth_tokens_credential_id", "auth_tokens", ["credential_id"])
    op.create_table(
        "consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("consent_type", sa.String(length=64), nullable=False),
        sa.Column("text_version", sa.String(length=64), nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("withdrawn_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "consent_type", name="uq_consents_user_type"),
    )
    op.create_index("ix_consents_user_id", "consents", ["user_id"])


def downgrade() -> None:
    """Remove identity tables and restore the provenance restrict rule."""
    op.drop_index("ix_consents_user_id", table_name="consents")
    op.drop_table("consents")
    op.drop_index("ix_auth_tokens_credential_id", table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_table("credentials")
    op.drop_constraint("provenance_entered_by_user_id_fkey", "provenance", type_="foreignkey")
    op.create_foreign_key(
        "provenance_entered_by_user_id_fkey",
        "provenance",
        "users",
        ["entered_by_user_id"],
        ["id"],
        ondelete="RESTRICT",
    )
