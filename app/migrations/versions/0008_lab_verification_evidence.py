"""Record evidence for manual organization verification.

Revision ID: 0008_lab_verification_evidence
Revises: 0007_lab_identity
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_lab_verification_evidence"
down_revision: str | None = "0007_lab_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add the timestamp and operator-provided evidence for manual review."""
    op.add_column(
        "organizations",
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("verification_reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("verified_by", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("verification_evidence", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    """Remove manual verification evidence fields."""
    op.drop_column("organizations", "verification_evidence")
    op.drop_column("organizations", "verified_by")
    op.drop_column("organizations", "verification_reviewed_at")
    op.drop_column("organizations", "verified_at")
