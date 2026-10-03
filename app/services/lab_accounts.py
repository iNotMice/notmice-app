"""Laboratory registration, authentication, and organization access gates."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Protocol
from uuid import UUID

import structlog

from app.core.security import (
    auth_token_digest,
    new_auth_token,
)
from app.domain.lab_accounts import (
    LabAccountNotFoundError,
    LabAuthTokenError,
    LabDuaUnavailableError,
    LabInvalidCredentialsError,
    LabLoginMaterial,
    LabOrganizationAccessError,
    LabUnauthenticatedError,
    LabUserRecord,
    LabVerificationStatus,
    lab_organization_values,
    normalized_lab_email,
)
from app.services.mailer import Mailer, OutboundMail

logger = structlog.get_logger(__name__)

_CONFIRM_PURPOSE = "confirm_email"
_TOKEN_TTL = timedelta(hours=24)
_SESSION_TTL = timedelta(hours=12)
_DUMMY_PASSWORD = "notmice-lab-login-timing-pad"
# Set only after legal approval of the laboratory data-use agreement.
CURRENT_DUA_VERSION: str | None = None


class LabAccountStore(Protocol):
    """Persistence contract for laboratory identity and access state."""

    async def create_organization_owner(
        self,
        *,
        name: str,
        org_type: str,
        country: str,
        email: str,
        password_hash: str,
    ) -> LabUserRecord: ...

    async def login_material(self, email: str) -> LabLoginMaterial | None: ...

    async def user_by_id(self, user_id: UUID) -> LabUserRecord | None: ...

    async def save_auth_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_sha256: str,
        expires_at: datetime,
        now: datetime,
    ) -> None: ...

    async def consume_auth_token(
        self,
        *,
        token_sha256: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None: ...

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None: ...

    async def open_session(
        self, *, user_id: UUID, token_sha256: str, expires_at: datetime
    ) -> None: ...

    async def user_for_session(self, token_sha256: str, now: datetime) -> LabUserRecord | None: ...

    async def revoke_session(self, token_sha256: str) -> None: ...

    async def accept_dua(
        self, organization_id: UUID, *, version: str, accepted_at: datetime
    ) -> bool: ...

    async def verify_organization(
        self,
        organization_id: UUID,
        *,
        status: LabVerificationStatus,
        operator: str,
        evidence: str,
        verified_at: datetime,
    ) -> bool: ...


class PasswordHasher(Protocol):
    """Password operations required by lab authentication."""

    def hash_password(self, password: str) -> str: ...

    def verify(self, password_hash: str, password: str) -> bool: ...

    def verify_dummy(self, password: str) -> None: ...


class LabAccountService:
    """Authenticate a lab organization separately from participant accounts."""

    def __init__(
        self,
        store: LabAccountStore,
        passwords: PasswordHasher,
        mailer: Mailer,
        *,
        app_url: str,
        token_ttl: timedelta = _TOKEN_TTL,
        session_ttl: timedelta = _SESSION_TTL,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._passwords = passwords
        self._mailer = mailer
        self._app_url = app_url.rstrip("/")
        self._token_ttl = token_ttl
        self._session_ttl = session_ttl
        self._now = now if now is not None else lambda: datetime.now(UTC)

    async def register(
        self,
        *,
        name: str,
        org_type: str,
        country: str,
        email: str,
        password: str,
    ) -> None:
        """Create a pending organization and send email confirmation."""
        normalized_name, normalized_type, normalized_country = lab_organization_values(
            name=name,
            org_type=org_type,
            country=country,
        )
        normalized_email = normalized_lab_email(email)
        self._require_password(password)
        existing = await self._store.login_material(normalized_email)
        if existing is not None:
            if existing.email_confirmed_at is None:
                await self._issue_confirmation(existing.user_id, normalized_email)
            return
        user = await self._store.create_organization_owner(
            name=normalized_name,
            org_type=normalized_type,
            country=normalized_country,
            email=normalized_email,
            password_hash=self._passwords.hash_password(password),
        )
        await self._issue_confirmation(user.id, normalized_email)
        logger.info("lab_account_registered", organization_id=str(user.organization_id))

    async def confirm_email(self, presented: str) -> tuple[LabUserRecord, str]:
        """Consume a one-time link and start the new lab user's session."""
        user_id = await self._consume_token(presented)
        now = self._now()
        await self._store.mark_email_confirmed(user_id, now)
        user = await self._store.user_by_id(user_id)
        if user is None:
            raise LabAccountNotFoundError
        return user, await self._open_session(user.id)

    async def login(self, email: str, password: str) -> tuple[LabUserRecord, str]:
        """Authenticate a confirmed lab user without exposing account state."""
        normalized_email = normalized_lab_email(email)
        material = await self._store.login_material(normalized_email)
        if material is None or material.email_confirmed_at is None:
            self._passwords.verify_dummy(password)
            raise LabInvalidCredentialsError
        if not self._passwords.verify(material.password_hash, password):
            raise LabInvalidCredentialsError
        user = await self._store.user_by_id(material.user_id)
        if user is None:
            raise LabInvalidCredentialsError
        return user, await self._open_session(user.id)

    async def authenticate(self, presented: str | None) -> LabUserRecord:
        """Resolve the separate lab cookie to a live session."""
        if presented is None or not presented.strip():
            raise LabUnauthenticatedError
        digest = auth_token_digest(presented.strip())
        if digest is None:
            raise LabUnauthenticatedError
        user = await self._store.user_for_session(digest, self._now())
        if user is None or user.email_confirmed_at is None:
            raise LabUnauthenticatedError
        return user

    async def logout(self, presented: str | None) -> None:
        """Revoke the current laboratory session."""
        if presented is None or not presented.strip():
            return
        digest = auth_token_digest(presented.strip())
        if digest is not None:
            await self._store.revoke_session(digest)

    async def require_verified_dua(self, user: LabUserRecord) -> LabUserRecord:
        """Enforce email, manual verification, and current DUA before lab data access."""
        if user.email_confirmed_at is None:
            raise LabUnauthenticatedError
        if user.organization.verification_status != "verified":
            raise LabOrganizationAccessError
        if CURRENT_DUA_VERSION is None:
            raise LabDuaUnavailableError
        if user.organization.dua_version != CURRENT_DUA_VERSION:
            raise LabOrganizationAccessError
        return user

    async def accept_current_dua(self, user: LabUserRecord) -> LabUserRecord:
        """Record explicit acceptance after verification and legal approval."""
        if user.email_confirmed_at is None:
            raise LabUnauthenticatedError
        if user.organization.verification_status != "verified":
            raise LabOrganizationAccessError
        if CURRENT_DUA_VERSION is None:
            raise LabDuaUnavailableError
        accepted = await self._store.accept_dua(
            user.organization_id,
            version=CURRENT_DUA_VERSION,
            accepted_at=self._now(),
        )
        if not accepted:
            raise LabOrganizationAccessError
        refreshed = await self._store.user_by_id(user.id)
        if refreshed is None:
            raise LabAccountNotFoundError
        return refreshed

    async def _issue_confirmation(self, user_id: UUID, email: str) -> None:
        presented, digest = new_auth_token()
        now = self._now()
        await self._store.save_auth_token(
            user_id=user_id,
            purpose=_CONFIRM_PURPOSE,
            token_sha256=digest,
            expires_at=now + self._token_ttl,
            now=now,
        )
        try:
            await self._mailer.send(
                OutboundMail(
                    to=email,
                    subject="Confirm your NotMice laboratory account",
                    body=(
                        "Open this link once. It expires after 24 hours.\n"
                        f"{self._app_url}/api/v1/lab/confirm?token={presented}\n"
                    ),
                )
            )
        except Exception:
            logger.exception("lab_auth_mail_failed")

    async def _consume_token(self, presented: str) -> UUID:
        digest = auth_token_digest(presented.strip())
        if digest is None:
            raise LabAuthTokenError
        user_id = await self._store.consume_auth_token(
            token_sha256=digest,
            purpose=_CONFIRM_PURPOSE,
            now=self._now(),
        )
        if user_id is None:
            raise LabAuthTokenError
        return user_id

    async def _open_session(self, user_id: UUID) -> str:
        presented, digest = new_auth_token()
        await self._store.open_session(
            user_id=user_id,
            token_sha256=digest,
            expires_at=self._now() + self._session_ttl,
        )
        return presented

    @staticmethod
    def _require_password(password: str) -> None:
        if len(password) < 12 or len(password) > 128:
            raise ValueError("Password must be between 12 and 128 characters")
