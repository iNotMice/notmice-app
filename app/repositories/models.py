"""SQLAlchemy ORM tables for the Phase 2 minimum schema."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.enums import MappingStatus


class Base(DeclarativeBase):
    """Declarative base for Alembic metadata."""


class User(Base):
    """Pseudonymous participant. No name, date of birth, or patient number."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    public_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    seed_phrase_hash: Mapped[str | None] = mapped_column(Text, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lab_results: Mapped[list[LabResult]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    share_settings: Mapped[ShareSettings | None] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    protocol_entries: Mapped[list[ProtocolEntryRow]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    participant_profile: Mapped[ParticipantProfileRow | None] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    profile_conditions: Mapped[list[ProfileCondition]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )


class LabResult(Base):
    """One confirmed (or pending) laboratory panel belonging to a user."""

    __tablename__ = "lab_results"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    collected_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chronological_age: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="lab_results")
    biomarkers: Mapped[list[Biomarker]] = relationship(back_populates="lab_result")
    provenance: Mapped[Provenance | None] = relationship(back_populates="lab_result")


class Biomarker(Base):
    """A single extracted or confirmed analyte row."""

    __tablename__ = "biomarkers"
    __table_args__ = (
        CheckConstraint(
            "mapping_status IN ('mapped', 'unmapped')",
            name="ck_biomarkers_mapping_status",
        ),
        CheckConstraint(
            "lab_flag IS NULL OR lab_flag IN ('H', 'L', '*')",
            name="ck_biomarkers_lab_flag",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lab_results.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    loinc_code: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    raw_name: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    value: Mapped[Decimal] = mapped_column(Numeric(14, 6), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    reported_value: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    reported_unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ref_low: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    ref_high: Mapped[Decimal | None] = mapped_column(Numeric(14, 6), nullable=True)
    ref_text: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lab_flag: Mapped[str | None] = mapped_column(String(1), nullable=True)
    mapping_status: Mapped[str] = mapped_column(
        String(16),
        default=MappingStatus.UNMAPPED.value,
        index=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lab_result: Mapped[LabResult] = relationship(back_populates="biomarkers")


class Provenance(Base):
    """Origin metadata for a lab result. Stores SHA-256 of the original file, never the file."""

    __tablename__ = "provenance"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lab_results.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    entered_by_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_sha256: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    parser_version: Mapped[str] = mapped_column(String(64), nullable=False)
    lab_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    collected_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    lab_result: Mapped[LabResult] = relationship(back_populates="provenance")


class ShareSettings(Base):
    """Opt-in public sharing flag. Default is private."""

    __tablename__ = "share_settings"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="share_settings")


class Credential(Base):
    """Email login material. Analyses reference ``users.id``, never this table."""

    __tablename__ = "credentials"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    email_confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class AuthToken(Base):
    """One-time confirmation or reset token. Only the SHA-256 digest is stored."""

    __tablename__ = "auth_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('confirm_email', 'reset_password')",
            name="ck_auth_tokens_purpose",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    credential_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("credentials.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class LoginSession(Base):
    """A server session. Only the SHA-256 of the cookie value is stored."""

    __tablename__ = "login_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Consent(Base):
    """A grant of a named text version, and the moment it was withdrawn."""

    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    consent_type: Mapped[str] = mapped_column(String(64), nullable=False)
    text_version: Mapped[str] = mapped_column(String(64), nullable=False)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ParticipantProfileRow(Base):
    """Controlled, optional survey answers belonging to one participant."""

    __tablename__ = "participant_profiles"
    __table_args__ = (
        CheckConstraint(
            "year_of_birth IS NULL OR year_of_birth BETWEEN 1900 AND 2015",
            name="ck_profiles_year_of_birth",
        ),
        CheckConstraint(
            "country IS NULL OR (length(country) = 2 AND country = upper(country))",
            name="ck_profiles_country_code",
        ),
        CheckConstraint(
            "sex_at_birth IS NULL OR sex_at_birth IN ('female', 'male', 'intersex', 'undisclosed')",
            name="ck_profiles_sex_at_birth",
        ),
        CheckConstraint(
            "smoking IS NULL OR smoking IN ('never', 'former', 'current')",
            name="ck_profiles_smoking",
        ),
        CheckConstraint(
            "alcohol IS NULL OR alcohol IN ('none', 'light', 'moderate', 'heavy')",
            name="ck_profiles_alcohol",
        ),
        CheckConstraint(
            "activity IS NULL OR activity IN ('sedentary', 'light', 'moderate', 'high')",
            name="ck_profiles_activity",
        ),
        CheckConstraint(
            "height_cm IS NULL OR height_cm BETWEEN 100 AND 250",
            name="ck_profiles_height_cm",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg BETWEEN 30 AND 400",
            name="ck_profiles_weight_kg",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    sex_at_birth: Mapped[str | None] = mapped_column(String(16), nullable=True)
    year_of_birth: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    smoking: Mapped[str | None] = mapped_column(String(16), nullable=True)
    alcohol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    activity: Mapped[str | None] = mapped_column(String(16), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="participant_profile")


class ProfileCondition(Base):
    """One code from the survey's controlled conditions vocabulary."""

    __tablename__ = "profile_conditions"
    __table_args__ = (UniqueConstraint("user_id", "code", name="uq_profile_conditions_user_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(48), nullable=False)
    user: Mapped[User] = relationship(back_populates="profile_conditions")


class ProtocolEntryRow(Base):
    """One protocol-journal row. It belongs to the participant, not to a research package.

    There is no catalog id. Deleting the participant removes the row.
    """

    __tablename__ = "protocol_entries"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('drug', 'supplement', 'nutrition', 'activity', 'sleep', 'other')",
            name="ck_protocol_entries_kind",
        ),
        CheckConstraint(
            "ended_on IS NULL OR ended_on >= started_on",
            name="ck_protocol_entries_period",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    kind: Mapped[str] = mapped_column(String(16), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_on: Mapped[date] = mapped_column(Date, nullable=False)
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped[User] = relationship(back_populates="protocol_entries")


class Organization(Base):
    """A data consumer that remains blocked until manual verification and DUA."""

    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint(
            "length(country) = 2 AND country = upper(country)",
            name="ck_organizations_country_code",
        ),
        CheckConstraint(
            "verification_status IN ('pending', 'verified', 'rejected')",
            name="ck_organizations_verification_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    org_type: Mapped[str] = mapped_column(String(32), nullable=False)
    country: Mapped[str] = mapped_column(String(2), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(16), default="pending", nullable=False)
    dua_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    dua_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(120))
    verification_evidence: Mapped[str | None] = mapped_column(String(1000))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class LabUser(Base):
    """Credentials for a laboratory user, isolated from participant identities."""

    __tablename__ = "lab_users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('owner', 'admin', 'member')",
            name="ck_lab_users_role",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="member", nullable=False)
    email_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class LabSession(Base):
    """A laboratory session stores only the digest of its cookie token."""

    __tablename__ = "lab_sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lab_users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class LabAuthToken(Base):
    """A single-use laboratory email-confirmation or password-reset token digest."""

    __tablename__ = "lab_auth_tokens"
    __table_args__ = (
        CheckConstraint(
            "purpose IN ('confirm_email', 'reset_password')",
            name="ck_lab_auth_tokens_purpose",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lab_users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_sha256: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class LabQueryAudit(Base):
    """Audit metadata for future aggregate-only lab requests."""

    __tablename__ = "lab_query_audit"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    lab_user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("lab_users.id"),
        index=True,
        nullable=False,
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("organizations.id"),
        index=True,
        nullable=False,
    )
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False)
    query: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    result_cohort_size: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
