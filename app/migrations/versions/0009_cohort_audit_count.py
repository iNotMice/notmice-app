"""Allow the cohort audit to retain rounded counts above 32767.

Revision ID: 0009_cohort_audit_count
Revises: 0008_lab_verification_evidence
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_cohort_audit_count"
down_revision: str | None = "0008_lab_verification_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Store large published cohort counts without truncation."""
    op.alter_column(
        "lab_query_audit",
        "result_cohort_size",
        existing_type=sa.SmallInteger(),
        type_=sa.Integer(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore the previous audit count width."""
    op.alter_column(
        "lab_query_audit",
        "result_cohort_size",
        existing_type=sa.Integer(),
        type_=sa.SmallInteger(),
        existing_nullable=True,
    )
