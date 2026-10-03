"""Optional controlled participant survey profile.

Revision ID: 0006_participant_profiles
Revises: 0005_protocol_entries
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_participant_profiles"
down_revision: str | None = "0005_protocol_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create participant profile storage, isolated from credentials."""
    op.create_table(
        "participant_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sex_at_birth", sa.String(length=16), nullable=True),
        sa.Column("year_of_birth", sa.SmallInteger(), nullable=True),
        sa.Column("country", sa.String(length=2), nullable=True),
        sa.Column("height_cm", sa.SmallInteger(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(5, 2), nullable=True),
        sa.Column("smoking", sa.String(length=16), nullable=True),
        sa.Column("alcohol", sa.String(length=16), nullable=True),
        sa.Column("activity", sa.String(length=16), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "year_of_birth IS NULL OR year_of_birth BETWEEN 1900 AND 2015",
            name="ck_profiles_year_of_birth",
        ),
        sa.CheckConstraint(
            "country IS NULL OR (length(country) = 2 AND country = upper(country))",
            name="ck_profiles_country_code",
        ),
        sa.CheckConstraint(
            "sex_at_birth IS NULL OR sex_at_birth IN ('female', 'male', 'intersex', 'undisclosed')",
            name="ck_profiles_sex_at_birth",
        ),
        sa.CheckConstraint(
            "smoking IS NULL OR smoking IN ('never', 'former', 'current')",
            name="ck_profiles_smoking",
        ),
        sa.CheckConstraint(
            "alcohol IS NULL OR alcohol IN ('none', 'light', 'moderate', 'heavy')",
            name="ck_profiles_alcohol",
        ),
        sa.CheckConstraint(
            "activity IS NULL OR activity IN ('sedentary', 'light', 'moderate', 'high')",
            name="ck_profiles_activity",
        ),
        sa.CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 100 AND 250",
            name="ck_profiles_height_cm",
        ),
        sa.CheckConstraint(
            "weight_kg IS NULL OR weight_kg BETWEEN 30 AND 400",
            name="ck_profiles_weight_kg",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_participant_profiles_user_id"),
    )
    op.create_table(
        "profile_conditions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("code", sa.String(length=48), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "code", name="uq_profile_conditions_user_code"),
    )
    op.create_index("ix_profile_conditions_user_id", "profile_conditions", ["user_id"])


def downgrade() -> None:
    """Remove optional survey storage."""
    op.drop_index("ix_profile_conditions_user_id", table_name="profile_conditions")
    op.drop_table("profile_conditions")
    op.drop_table("participant_profiles")
