"""Account use-cases. No FastAPI, no ORM models."""

from __future__ import annotations

import csv
import io
import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from app.core.security import (
    Argon2PasswordHasher,
    Argon2SeedHasher,
    JwtTokenIssuer,
    TokenError,
    auth_token_digest,
    generate_mnemonic,
    is_valid_mnemonic,
    new_auth_token,
    normalize_mnemonic,
)
from app.domain.accounts import (
    AccountExport,
    AccountNotFoundError,
    AuthenticatedSession,
    ConsentRecord,
    ConsentVersionError,
    CreatedAccount,
    EmailLogin,
    ExportedMarker,
    InvalidAuthTokenError,
    InvalidCredentialsError,
    InvalidMnemonicError,
    UnauthenticatedError,
    UserRecord,
)
from app.domain.consents import ConsentChoice, current_version, grants_to_store
from app.domain.pii import reject_pii
from app.services.mailer import Mailer, OutboundMail

logger = structlog.get_logger(__name__)

_PUBLIC_ID_BYTES = 8
_PUBLIC_ID_ATTEMPTS = 8
_PASSWORD_MIN = 12
_PASSWORD_MAX = 128
_TOKEN_TTL = timedelta(hours=24, minutes=30)
_PURPOSE_CONFIRM = "confirm_email"
_PURPOSE_RESET = "reset_password"


class UserStore(Protocol):
    """Persistence contract used by AccountService.

    Implementations that can see both an email and lab rows live behind this
    protocol. Other services do not join those tables.
    """

    async def create(self, *, public_id: str, seed_phrase_hash: str) -> UserRecord:
        """Insert a phrase account and default-private share settings."""

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        """Load by internal id."""

    async def get_by_public_id(self, public_id: str) -> UserRecord | None:
        """Load by public identifier."""

    async def get_by_seed_phrase_hash(self, seed_phrase_hash: str) -> UserRecord | None:
        """Load by argon2id encoding."""

    async def set_is_public(self, user_id: UUID, is_public: bool) -> UserRecord | None:
        """Update the opt-in sharing flag."""

    async def create_email_account(
        self,
        *,
        public_id: str,
        email: str,
        password_hash: str,
        consents: tuple[tuple[str, str], ...],
        granted_at: datetime,
    ) -> UserRecord:
        """Insert a participant plus a separate credentials row."""

    async def find_email(self, email: str) -> EmailLogin | None:
        """Load password material for a normalized address."""

    async def save_auth_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_sha256: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        """Store a token digest and retire older unused tokens of that purpose."""

    async def consume_auth_token(
        self,
        *,
        token_sha256: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        """Consume a one-time token and return the participant id."""

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None:
        """Record that the address was confirmed."""

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> None:
        """Replace the stored password hash."""

    async def list_consents(self, user_id: UUID) -> tuple[ConsentRecord, ...]:
        """Return consent rows for the participant."""

    async def set_consent(
        self,
        *,
        user_id: UUID,
        consent_type: str,
        text_version: str,
        accepted: bool,
        now: datetime,
    ) -> ConsentRecord | None:
        """Grant or withdraw one consent."""

    async def delete_account(self, user_id: UUID) -> bool:
        """Delete the participant and cascaded rows."""

    async def export_account(self, user_id: UUID) -> AccountExport | None:
        """Return the owner's copy of the account, including the address."""


def new_public_id() -> str:
    """Return a random public identifier such as ``nm`` + 16 hex chars."""
    return f"nm{secrets.token_hex(_PUBLIC_ID_BYTES)}"


class AccountService:
    """Create, authenticate, and update share settings for pseudonymous users."""

    def __init__(
        self,
        users: UserStore,
        hasher: Argon2SeedHasher,
        tokens: JwtTokenIssuer,
        passwords: Argon2PasswordHasher | None = None,
        mailer: Mailer | None = None,
        *,
        auth_seed_enabled: bool = True,
        app_url: str = "http://localhost:8080",
        token_ttl: timedelta = _TOKEN_TTL,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._users = users
        self._hasher = hasher
        self._tokens = tokens
        self._passwords = passwords if passwords is not None else Argon2PasswordHasher()
        self._mailer = mailer
        self._auth_seed_enabled = auth_seed_enabled
        self._app_url = app_url.rstrip("/")
        self._token_ttl = token_ttl
        self._now = now if now is not None else _utc_now

    async def create(self) -> CreatedAccount:
        """Generate a BIP-39 phrase, store only its argon2id hash, return the phrase once."""
        mnemonic = generate_mnemonic()
        seed_phrase_hash = self._hasher.hash_phrase(mnemonic)
        public_id = await self._allocate_public_id()
        user = await self._users.create(public_id=public_id, seed_phrase_hash=seed_phrase_hash)
        access_token = self._tokens.issue(user.id, user.public_id)
        logger.info("account_created", public_id=user.public_id)
        return CreatedAccount(user=user, mnemonic=mnemonic, access_token=access_token)

    async def login(self, mnemonic_raw: str) -> AuthenticatedSession:
        """Authenticate with a recovery phrase.

        Args:
            mnemonic_raw: User-supplied phrase. Normalized and checksum-checked.

        Raises:
            InvalidMnemonicError: Phrase is not valid BIP-39.
            InvalidCredentialsError: Phrase is valid but matches no account.
        """
        if not self._auth_seed_enabled:
            raise InvalidCredentialsError
        reject_pii({"mnemonic": mnemonic_raw})
        mnemonic = normalize_mnemonic(mnemonic_raw)
        if not is_valid_mnemonic(mnemonic):
            raise InvalidMnemonicError
        seed_phrase_hash = self._hasher.hash_phrase(mnemonic)
        user = await self._users.get_by_seed_phrase_hash(seed_phrase_hash)
        if user is None:
            raise InvalidCredentialsError
        access_token = self._tokens.issue(user.id, user.public_id)
        logger.info("account_login", public_id=user.public_id)
        return AuthenticatedSession(user=user, access_token=access_token)

    async def authenticate(self, token: str | None) -> UserRecord:
        """Resolve a bearer token to a user.

        Args:
            token: Raw JWT, or None if the header was missing.

        Raises:
            UnauthenticatedError: Token missing or invalid.
            AccountNotFoundError: Subject was deleted.
        """
        if token is None or token.strip() == "":
            raise UnauthenticatedError
        try:
            claims = self._tokens.parse(token)
        except TokenError as exc:
            raise UnauthenticatedError from exc
        user = await self._users.get_by_id(claims.user_id)
        if user is None:
            raise AccountNotFoundError
        return user

    async def set_public(self, user_id: UUID, is_public: bool) -> UserRecord:
        """Persist the opt-in sharing toggle.

        Args:
            user_id: Authenticated user.
            is_public: New flag value.

        Raises:
            AccountNotFoundError: User no longer exists.
        """
        user = await self._users.set_is_public(user_id, is_public)
        if user is None:
            raise AccountNotFoundError
        logger.info("share_settings_updated", public_id=user.public_id, is_public=is_public)
        return user

    async def register(
        self,
        *,
        email: str,
        password: str,
        consents: tuple[ConsentChoice, ...],
    ) -> None:
        """Create an email account or resend confirmation. The HTTP result is always the same.

        New accounts do not receive a recovery phrase. An address that already
        exists produces no distinct outcome for the caller.

        Args:
            email: Address, normalized by the caller.
            password: At least 12 characters.
            consents: Checkbox choices. Optional consents that are off are omitted.

        Raises:
            ConsentRequiredError: The health-data consent is missing or declined.
            ConsentVersionError: A consent text version is not current.
        """
        _require_password(password)
        granted = grants_to_store(consents)
        password_hash = self._passwords.hash_password(password)
        existing = await self._users.find_email(email)
        now = self._now()
        if existing is None:
            public_id = await self._allocate_public_id()
            user = await self._users.create_email_account(
                public_id=public_id,
                email=email,
                password_hash=password_hash,
                consents=granted,
                granted_at=now,
            )
            await self._issue_token(user.id, _PURPOSE_CONFIRM, email, now)
            logger.info("account_registered", public_id=user.public_id)
            return
        if existing.email_confirmed_at is None:
            await self._issue_token(existing.user_id, _PURPOSE_CONFIRM, email, now)
        logger.info("account_register_unchanged")

    async def login_email(self, email: str, password: str) -> AuthenticatedSession:
        """Sign in with email and password.

        Unknown addresses, wrong passwords, and unconfirmed addresses share one error.

        Args:
            email: Normalized address.
            password: Raw password.

        Raises:
            InvalidCredentialsError: The pair does not open a confirmed account.
        """
        existing = await self._users.find_email(email)
        if existing is None or existing.email_confirmed_at is None:
            self._passwords.verify_dummy(password)
            raise InvalidCredentialsError
        if not self._passwords.verify(existing.password_hash, password):
            raise InvalidCredentialsError
        user = await self._users.get_by_id(existing.user_id)
        if user is None:
            raise InvalidCredentialsError
        access_token = self._tokens.issue(user.id, user.public_id)
        logger.info("account_email_login", public_id=user.public_id)
        return AuthenticatedSession(user=user, access_token=access_token)

    async def confirm_email(self, presented: str) -> AuthenticatedSession:
        """Consume a confirmation token and sign the participant in.

        Args:
            presented: Raw token from the link.

        Raises:
            InvalidAuthTokenError: The token is unknown, used, or expired.
            AccountNotFoundError: The participant row disappeared.
        """
        user_id = await self._consume(presented, _PURPOSE_CONFIRM)
        now = self._now()
        await self._users.mark_email_confirmed(user_id, now)
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise AccountNotFoundError
        access_token = self._tokens.issue(user.id, user.public_id)
        logger.info("email_confirmed", public_id=user.public_id)
        return AuthenticatedSession(user=user, access_token=access_token)

    async def request_password_reset(self, email: str) -> None:
        """Send a reset link when the address belongs to a confirmed account.

        Args:
            email: Normalized address. Missing and unconfirmed addresses send nothing.
        """
        existing = await self._users.find_email(email)
        if existing is None or existing.email_confirmed_at is None:
            return
        await self._issue_token(existing.user_id, _PURPOSE_RESET, email, self._now())

    async def reset_password(self, presented: str, password: str) -> None:
        """Set a new password with a one-time token.

        Args:
            presented: Raw token from the link.
            password: New password, at least 12 characters.

        Raises:
            InvalidAuthTokenError: The token is unknown, used, or expired.
        """
        _require_password(password)
        user_id = await self._consume(presented, _PURPOSE_RESET)
        password_hash = self._passwords.hash_password(password)
        await self._users.set_password_hash(user_id, password_hash)
        logger.info("password_reset")

    async def list_consents(self, user_id: UUID) -> tuple[ConsentRecord, ...]:
        """Return consent rows for the authenticated participant."""
        return await self._users.list_consents(user_id)

    async def set_consent(
        self,
        user_id: UUID,
        choice: ConsentChoice,
    ) -> ConsentRecord | None:
        """Grant or withdraw one catalogue consent.

        Args:
            user_id: Authenticated participant.
            choice: Type, current text version, and whether it is accepted.

        Raises:
            ConsentVersionError: The type or text version is not current.
        """
        version = current_version(choice.consent_type)
        if version is None or choice.text_version != version:
            raise ConsentVersionError
        return await self._users.set_consent(
            user_id=user_id,
            consent_type=choice.consent_type,
            text_version=version,
            accepted=choice.accepted,
            now=self._now(),
        )

    async def delete_account(self, user_id: UUID) -> None:
        """Delete the participant and the rows that cascade from them.

        Args:
            user_id: Authenticated participant.

        Raises:
            AccountNotFoundError: The participant is already gone.
        """
        deleted = await self._users.delete_account(user_id)
        if not deleted:
            raise AccountNotFoundError
        logger.info("account_deleted")

    async def export_json(self, user_id: UUID) -> str:
        """Return the owner's account as JSON.

        Args:
            user_id: Authenticated participant.

        Raises:
            AccountNotFoundError: The participant is already gone.
        """
        bundle = await self._require_export(user_id)
        payload = {
            "public_id": bundle.public_id,
            "email": bundle.email,
            "is_public": bundle.is_public,
            "created_at": bundle.created_at.isoformat(),
            "consents": [
                {
                    "type": row.consent_type,
                    "version": row.text_version,
                    "granted_at": row.granted_at.isoformat(),
                    "withdrawn_at": None
                    if row.withdrawn_at is None
                    else row.withdrawn_at.isoformat(),
                }
                for row in bundle.consents
            ],
            "markers": [_marker_dict(row) for row in bundle.markers],
        }
        return json.dumps(payload, ensure_ascii=False)

    async def export_csv(self, user_id: UUID) -> str:
        """Return the owner's confirmed analytes as CSV.

        Args:
            user_id: Authenticated participant.

        Raises:
            AccountNotFoundError: The participant is already gone.
        """
        bundle = await self._require_export(user_id)
        buffer = io.StringIO()
        writer = csv.DictWriter(
            buffer,
            fieldnames=(
                "public_id",
                "email",
                "collected_at",
                "lab_name",
                "raw_name",
                "loinc_code",
                "value",
                "unit",
                "ref_low",
                "ref_high",
                "lab_flag",
            ),
        )
        writer.writeheader()
        for row in bundle.markers:
            writer.writerow(
                {
                    "public_id": bundle.public_id,
                    "email": bundle.email or "",
                    "collected_at": ""
                    if row.collected_at is None
                    else row.collected_at.isoformat(),
                    "lab_name": row.lab_name or "",
                    "raw_name": row.raw_name,
                    "loinc_code": row.loinc_code or "",
                    "value": _decimal_text(row.value),
                    "unit": row.unit,
                    "ref_low": "" if row.ref_low is None else _decimal_text(row.ref_low),
                    "ref_high": "" if row.ref_high is None else _decimal_text(row.ref_high),
                    "lab_flag": row.lab_flag or "",
                }
            )
        return buffer.getvalue()

    async def _issue_token(self, user_id: UUID, purpose: str, email: str, now: datetime) -> None:
        """Store a digest and mail the raw token. Mail failures stay off the HTTP result."""
        presented, digest = new_auth_token()
        await self._users.save_auth_token(
            user_id=user_id,
            purpose=purpose,
            token_sha256=digest,
            expires_at=now + self._token_ttl,
            now=now,
        )
        if self._mailer is None:
            return
        query = "confirm" if purpose == _PURPOSE_CONFIRM else "reset"
        link = f"{self._app_url}/?{query}={presented}"
        subject = (
            "Confirm your NotMice account"
            if purpose == _PURPOSE_CONFIRM
            else "Reset your NotMice password"
        )
        body = f"Open this link once. It expires after 24 hours and 30 minutes.\n{link}\n"
        try:
            await self._mailer.send(OutboundMail(to=email, subject=subject, body=body))
        except Exception:
            logger.exception("auth_mail_failed")

    async def _consume(self, presented: str, purpose: str) -> UUID:
        """Return the participant id for a live token.

        Raises:
            InvalidAuthTokenError: The token cannot be used.
        """
        digest = auth_token_digest(presented.strip())
        if digest is None:
            raise InvalidAuthTokenError
        user_id = await self._users.consume_auth_token(
            token_sha256=digest,
            purpose=purpose,
            now=self._now(),
        )
        if user_id is None:
            raise InvalidAuthTokenError
        return user_id

    async def _require_export(self, user_id: UUID) -> AccountExport:
        """Load the owner's export or raise when the account is gone."""
        bundle = await self._users.export_account(user_id)
        if bundle is None:
            raise AccountNotFoundError
        return bundle

    async def _allocate_public_id(self) -> str:
        """Generate a unique public_id, retrying on the vanishingly rare collision."""
        for _ in range(_PUBLIC_ID_ATTEMPTS):
            candidate = new_public_id()
            existing = await self._users.get_by_public_id(candidate)
            if existing is None:
                return candidate
        raise RuntimeError("Unable to allocate a unique public_id")


def _utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


def _require_password(password: str) -> None:
    """Reject passwords outside 12-128 characters.

    Raises:
        InvalidCredentialsError: The password cannot be stored.
    """
    if len(password) < _PASSWORD_MIN or len(password) > _PASSWORD_MAX:
        raise InvalidCredentialsError


def _decimal_text(value: Decimal) -> str:
    """Render a decimal without binary float noise or trailing zeros."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _marker_dict(row: ExportedMarker) -> dict[str, str | None]:
    """One analyte object for the owner's JSON export."""
    return {
        "collected_at": None if row.collected_at is None else row.collected_at.isoformat(),
        "lab_name": row.lab_name,
        "raw_name": row.raw_name,
        "loinc_code": row.loinc_code,
        "value": _decimal_text(row.value),
        "unit": row.unit,
        "ref_low": None if row.ref_low is None else _decimal_text(row.ref_low),
        "ref_high": None if row.ref_high is None else _decimal_text(row.ref_high),
        "lab_flag": row.lab_flag,
    }
