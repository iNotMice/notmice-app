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
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
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

    lab_results: Mapped[list[LabResult]] = relationship(back_populates="user")
    share_settings: Mapped[ShareSettings | None] = relationship(back_populates="user")
    protocol_entries: Mapped[list[ProtocolEntryRow]] = relationship(
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
        ForeignKey("users.id", ondelete="RESTRICT"),
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
    __table_args__ = (UniqueConstraint("user_id", "consent_type", name="uq_consents_user_type"),)

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
