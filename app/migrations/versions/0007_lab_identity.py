"""Isolated laboratory identity and cohort audit schema.

Revision ID: 0007_lab_identity
Revises: 0006_participant_profiles
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_lab_identity"
down_revision: str | None = "0006_participant_profiles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create a lab-only identity boundary, sessions, tokens, and query audit."""
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("org_type", sa.String(length=32), nullable=False),
        sa.Column("country", sa.String(length=2), nullable=False),
        sa.Column(
            "verification_status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("dua_version", sa.String(length=32), nullable=True),
        sa.Column("dua_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(country) = 2 AND country = upper(country)",
            name="ck_organizations_country_code",
        ),
        sa.CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected')",
            name="ck_organizations_verification_status",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "lab_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(length=16), server_default="member", nullable=False),
        sa.Column("email_confirmed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_lab_users_role",
        ),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_lab_users_organization_id", "lab_users", ["organization_id"])
    op.create_table(
        "lab_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_sha256", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lab_user_id"], ["lab_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_sha256"),
    )
    op.create_index("ix_lab_sessions_lab_user_id", "lab_sessions", ["lab_user_id"])
    op.create_table(
        "lab_auth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_user_id", postgresql.UUID(as_uuid=True), nullable=False),
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
            name="ck_lab_auth_tokens_purpose",
        ),
        sa.ForeignKeyConstraint(["lab_user_id"], ["lab_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_sha256"),
    )
    op.create_index("ix_lab_auth_tokens_lab_user_id", "lab_auth_tokens", ["lab_user_id"])
    op.create_table(
        "lab_query_audit",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lab_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("endpoint", sa.String(length=64), nullable=False),
        sa.Column("query", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result_cohort_size", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["lab_user_id"], ["lab_users.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lab_query_audit_lab_user_id", "lab_query_audit", ["lab_user_id"])
    op.create_index("ix_lab_query_audit_organization_id", "lab_query_audit", ["organization_id"])


def downgrade() -> None:
    """Remove the lab identity schema in dependency order."""
    op.drop_index("ix_lab_query_audit_organization_id", table_name="lab_query_audit")
    op.drop_index("ix_lab_query_audit_lab_user_id", table_name="lab_query_audit")
    op.drop_table("lab_query_audit")
    op.drop_index("ix_lab_auth_tokens_lab_user_id", table_name="lab_auth_tokens")
    op.drop_table("lab_auth_tokens")
    op.drop_index("ix_lab_sessions_lab_user_id", table_name="lab_sessions")
    op.drop_table("lab_sessions")
    op.drop_index("ix_lab_users_organization_id", table_name="lab_users")
    op.drop_table("lab_users")
    op.drop_table("organizations")
