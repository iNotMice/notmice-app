"""Account domain records and errors. No I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

_EMAIL_RE = re.compile(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}$")
_EMAIL_MAX_LENGTH = 254


class AccountError(Exception):
    """Base error for account use-cases."""


class InvalidMnemonicError(AccountError):
    """The submitted phrase is not a valid BIP-39 mnemonic."""


class InvalidCredentialsError(AccountError):
    """Phrase does not match any stored argon2id hash, or the token is bad."""


class UnauthenticatedError(AccountError):
    """A protected route was called without a usable access token."""


class AccountNotFoundError(AccountError):
    """The authenticated subject no longer exists."""


class InvalidAuthTokenError(AccountError):
    """A confirmation or reset token is unknown, used, or expired."""


class ConsentRequiredError(AccountError):
    """Registration is missing the required health-data consent."""


class ConsentVersionError(AccountError):
    """The submitted consent text version is not the current one."""


def normalize_email(value: str) -> str:
    """Return a lowercase email, or raise ValueError when it is not one address.

    Args:
        value: Raw address from a form.
    """
    text = value.strip().casefold()
    if len(text) > _EMAIL_MAX_LENGTH or _EMAIL_RE.fullmatch(text) is None:
        raise ValueError("Invalid email address")
    return text


@dataclass(frozen=True, slots=True)
class UserRecord:
    """Pseudonymous participant as seen by services. Never includes the phrase."""

    id: UUID
    public_id: str
    is_public: bool
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CreatedAccount:
    """Result of phrase-account creation. The mnemonic is present only here, once."""

    user: UserRecord
    mnemonic: str
    session_token: str


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    """A signed-in participant and the raw cookie value, returned once."""

    user: UserRecord
    session_token: str


@dataclass(frozen=True, slots=True)
class EmailLogin:
    """Password check material. The address itself stays in the credentials table."""

    user_id: UUID
    password_hash: str
    email_confirmed_at: datetime | None


@dataclass(frozen=True, slots=True)
class ConsentRecord:
    """One consent row. Withdrawal is a timestamp, not a deleted row."""

    consent_type: str
    text_version: str
    granted_at: datetime
    withdrawn_at: datetime | None


@dataclass(frozen=True, slots=True)
class ExportedMarker:
    """One confirmed analyte in the owner's own export. No internal ids."""

    collected_at: date | None
    lab_name: str | None
    raw_name: str
    loinc_code: str | None
    value: Decimal
    unit: str
    ref_low: Decimal | None
    ref_high: Decimal | None
    lab_flag: str | None


@dataclass(frozen=True, slots=True)
class AccountExport:
    """The signed-in person's copy of their account. Built only by the account repository."""

    public_id: str
    email: str | None
    is_public: bool
    created_at: datetime
    consents: tuple[ConsentRecord, ...]
    markers: tuple[ExportedMarker, ...]
