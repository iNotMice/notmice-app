"""Store the printed lab interval and unit beside the normalized value.

Revision ID: 0002_biomarker_reference
Revises: 0001_initial_schema
Create Date: 2026-09-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_biomarker_reference"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add nullable reference columns. Existing rows stay valid with nulls."""
    op.add_column(
        "biomarkers",
        sa.Column("reported_value", sa.Numeric(precision=14, scale=6), nullable=True),
    )
    op.add_column("biomarkers", sa.Column("reported_unit", sa.String(length=32), nullable=True))
    op.add_column(
        "biomarkers",
        sa.Column("ref_low", sa.Numeric(precision=14, scale=6), nullable=True),
    )
    op.add_column(
        "biomarkers",
        sa.Column("ref_high", sa.Numeric(precision=14, scale=6), nullable=True),
    )
    op.add_column("biomarkers", sa.Column("ref_text", sa.String(length=64), nullable=True))
    op.add_column("biomarkers", sa.Column("lab_flag", sa.String(length=1), nullable=True))
    op.create_check_constraint(
        "ck_biomarkers_lab_flag",
        "biomarkers",
        "lab_flag IS NULL OR lab_flag IN ('H', 'L', '*')",
    )


def downgrade() -> None:
    """Remove the printed-interval columns."""
    op.drop_constraint("ck_biomarkers_lab_flag", "biomarkers", type_="check")
    op.drop_column("biomarkers", "lab_flag")
    op.drop_column("biomarkers", "ref_text")
    op.drop_column("biomarkers", "ref_high")
    op.drop_column("biomarkers", "ref_low")
    op.drop_column("biomarkers", "reported_unit")
    op.drop_column("biomarkers", "reported_value")
