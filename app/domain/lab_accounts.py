"""Laboratory identity records and errors. No I/O."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

import pycountry

from app.domain.accounts import normalize_email

_ORG_NAME_MAX = 200
_ORG_TYPES = frozenset({"laboratory", "university", "research_institute", "company", "other"})
_COUNTRY_CODE = re.compile(r"^[A-Z]{2}$")
LabVerificationStatus = Literal["pending", "verified", "rejected"]


class LabAccountError(Exception):
    """Base error for laboratory identity use-cases."""


class LabInvalidCredentialsError(LabAccountError):
    """Credentials do not match a confirmed laboratory account."""


class LabUnauthenticatedError(LabAccountError):
    """A lab route was called without a live lab session."""


class LabAuthTokenError(LabAccountError):
    """A lab confirmation token is unknown, expired, or already used."""


class LabAccountNotFoundError(LabAccountError):
    """The lab user or organization no longer exists."""


class LabOrganizationAccessError(LabAccountError):
    """Organization verification or DUA requirements are not met."""


class LabDuaUnavailableError(LabAccountError):
    """The DUA has no legally approved current version."""


def lab_organization_values(
    *,
    name: str,
    org_type: str,
    country: str,
) -> tuple[str, str, str]:
    """Normalize and validate the public organization registration fields."""
    normalized_name = " ".join(name.split())
    if not normalized_name or len(normalized_name) > _ORG_NAME_MAX:
        raise ValueError("Invalid organization name")
    if org_type not in _ORG_TYPES:
        raise ValueError("Invalid organization type")
    if _COUNTRY_CODE.fullmatch(country) is None:
        raise ValueError("Invalid country code")
    if pycountry.countries.get(alpha_2=country) is None:
        raise ValueError("Unknown ISO-3166-1 alpha-2 country code")
    return normalized_name, org_type, country


@dataclass(frozen=True, slots=True)
class LabOrganizationRecord:
    """Organization state visible to its own authenticated members."""

    id: UUID
    name: str
    org_type: str
    country: str
    verification_status: LabVerificationStatus
    dua_version: str | None
    dua_accepted_at: datetime | None
    verified_at: datetime | None
    verification_reviewed_at: datetime | None
    verified_by: str | None
    verification_evidence: str | None


@dataclass(frozen=True, slots=True)
class LabUserRecord:
    """Authenticated lab user without password or token material."""

    id: UUID
    organization_id: UUID
    email: str
    role: str
    email_confirmed_at: datetime | None
    organization: LabOrganizationRecord


@dataclass(frozen=True, slots=True)
class LabLoginMaterial:
    """Credential material used only inside lab authentication."""

    user_id: UUID
    password_hash: str
    email_confirmed_at: datetime | None


def normalized_lab_email(value: str) -> str:
    """Use the participant email normalization rules for laboratory logins."""
    return normalize_email(value)


# Free mailbox providers. A laboratory registers with its own domain so the
# manual review can tie the account to the organization.
FREE_EMAIL_DOMAINS: frozenset[str] = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "live.com",
        "msn.com",
        "yahoo.com",
        "ymail.com",
        "icloud.com",
        "me.com",
        "mac.com",
        "aol.com",
        "gmx.com",
        "gmx.de",
        "gmx.net",
        "web.de",
        "t-online.de",
        "mail.com",
        "proton.me",
        "protonmail.com",
        "pm.me",
        "tutanota.com",
        "tuta.io",
        "zoho.com",
        "yandex.ru",
        "yandex.com",
        "ya.ru",
        "yandex.by",
        "yandex.kz",
        "mail.ru",
        "inbox.ru",
        "list.ru",
        "bk.ru",
        "internet.ru",
        "rambler.ru",
        "tut.by",
        "ukr.net",
        "i.ua",
        "wp.pl",
        "o2.pl",
        "onet.pl",
        "interia.pl",
        "op.pl",
        "seznam.cz",
        "libero.it",
        "orange.fr",
        "free.fr",
        "laposte.net",
        "qq.com",
        "163.com",
        "126.com",
        "mailinator.com",
        "guerrillamail.com",
        "10minutemail.com",
        "temp-mail.org",
        "yopmail.com",
    }
)


class LabPersonalEmailError(ValueError):
    """A laboratory tried to register with a free personal mailbox."""


def require_work_email(email: str) -> None:
    """Reject free mailbox providers for a new laboratory owner.

    Args:
        email: Already-normalized address.

    Raises:
        LabPersonalEmailError: The domain is a known free or disposable mailbox.
    """
    domain = email.rsplit("@", 1)[-1]
    if domain in FREE_EMAIL_DOMAINS:
        raise LabPersonalEmailError("A work email address of the organization is required")
