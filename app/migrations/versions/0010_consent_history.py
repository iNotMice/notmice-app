"""Allow append-only consent grants and withdrawals.

Revision ID: 0010_consent_history
Revises: 0009_cohort_audit_count
"""

from __future__ import annotations

from alembic import op

revision: str = "0010_consent_history"
down_revision: str | None = "0009_cohort_audit_count"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.drop_constraint("uq_consents_user_type", "consents", type_="unique")
    op.create_index(
        "ix_consents_user_type_granted_at",
        "consents",
        ["user_id", "consent_type", "granted_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_consents_user_type_granted_at", table_name="consents")
    op.create_unique_constraint(
        "uq_consents_user_type",
        "consents",
        ["user_id", "consent_type"],
    )
