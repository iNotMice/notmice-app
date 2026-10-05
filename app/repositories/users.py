"""User, credentials, consents, and the owner's own export. No HTTP, no hashing.

Email and analyses are joined only in this module.
"""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.accounts import (
    AccountExport,
    ConsentRecord,
    EmailLogin,
    ExportedMarker,
    ExportedProtocolEntry,
    OwnCredential,
    UserRecord,
)
from app.domain.survey import (
    Activity,
    Alcohol,
    ParticipantProfile,
    SexAtBirth,
    Smoking,
)
from app.repositories.models import (
    AuthToken,
    Biomarker,
    Consent,
    Credential,
    LabResult,
    LoginSession,
    ProtocolEntryRow,
    ShareSettings,
    User,
)


def _to_record(user: User) -> UserRecord:
    """Map an ORM row to a domain record.

    Args:
        user: SQLAlchemy user, optionally with share_settings loaded.
    """
    is_public = user.share_settings.is_public if user.share_settings is not None else False
    return UserRecord(
        id=user.id,
        public_id=user.public_id,
        is_public=is_public,
        created_at=user.created_at,
    )


class UserRepository:
    """Async access to ``users`` and ``share_settings``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, public_id: str, seed_phrase_hash: str) -> UserRecord:
        """Insert a private user. The phrase itself must never be passed here.

        Args:
            public_id: Unique public identifier.
            seed_phrase_hash: PHC-encoded argon2id hash.
        """
        user = User(id=uuid4(), public_id=public_id, seed_phrase_hash=seed_phrase_hash)
        settings = ShareSettings(id=uuid4(), user_id=user.id, is_public=False)
        self._session.add(user)
        self._session.add(settings)
        await self._session.flush()
        await self._session.refresh(user)
        user.share_settings = settings
        return _to_record(user)

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        """Return the user with share settings, or None."""
        result = await self._session.execute(
            select(User).options(selectinload(User.share_settings)).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        return _to_record(user) if user is not None else None

    async def get_by_public_id(self, public_id: str) -> UserRecord | None:
        """Return the user with this public_id, or None."""
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.share_settings))
            .where(User.public_id == public_id)
        )
        user = result.scalar_one_or_none()
        return _to_record(user) if user is not None else None

    async def get_by_seed_phrase_hash(self, seed_phrase_hash: str) -> UserRecord | None:
        """Look up a user by the stored argon2id encoding, or None."""
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.share_settings))
            .where(User.seed_phrase_hash == seed_phrase_hash)
        )
        user = result.scalar_one_or_none()
        return _to_record(user) if user is not None else None

    async def set_is_public(self, user_id: UUID, is_public: bool) -> UserRecord | None:
        """Upsert share_settings.is_public for the user. Returns None if missing."""
        result = await self._session.execute(
            select(User)
            .options(
                selectinload(User.share_settings),
                selectinload(User.participant_profile),
                selectinload(User.profile_conditions),
            )
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        if user.share_settings is None:
            user.share_settings = ShareSettings(id=uuid4(), user_id=user.id, is_public=is_public)
            self._session.add(user.share_settings)
        else:
            user.share_settings.is_public = is_public
        await self._session.flush()
        return _to_record(user)

    async def create_email_account(
        self,
        *,
        public_id: str,
        email: str,
        password_hash: str,
        consents: tuple[tuple[str, str], ...],
        granted_at: datetime,
    ) -> UserRecord:
        """Insert a participant, a credentials row, and the accepted consents.

        The participant row has no email and no password hash.

        Args:
            public_id: Unique public identifier.
            email: Normalized address. Stored only on ``credentials``.
            password_hash: PHC-encoded argon2id hash.
            consents: Pairs of consent type and text version.
            granted_at: Timestamp stored on each new consent row.
        """
        user = User(id=uuid4(), public_id=public_id, seed_phrase_hash=None)
        self._session.add(user)
        # Consent and Credential reference users.id and have no relationship(),
        # so a single flush can INSERT them before the participant. Postgres
        # then rejects consents_user_id_fkey. The user row must exist first.
        await self._session.flush()
        settings = ShareSettings(id=uuid4(), user_id=user.id, is_public=False)
        credential = Credential(
            id=uuid4(),
            user_id=user.id,
            email=email,
            password_hash=password_hash,
        )
        self._session.add(settings)
        self._session.add(credential)
        for consent_type, text_version in consents:
            self._session.add(
                Consent(
                    id=uuid4(),
                    user_id=user.id,
                    consent_type=consent_type,
                    text_version=text_version,
                    granted_at=granted_at,
                )
            )
        await self._session.flush()
        await self._session.refresh(user)
        user.share_settings = settings
        return _to_record(user)

    async def find_email(self, email: str) -> EmailLogin | None:
        """Return password material for a normalized address, or None.

        Args:
            email: Already-normalized address.
        """
        result = await self._session.execute(select(Credential).where(Credential.email == email))
        credential = result.scalar_one_or_none()
        if credential is None:
            return None
        return EmailLogin(
            user_id=credential.user_id,
            password_hash=credential.password_hash,
            email_confirmed_at=credential.email_confirmed_at,
        )

    async def save_auth_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_sha256: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        """Store a new digest and retire older unused tokens of the same purpose.

        Args:
            user_id: Participant who owns the credentials row.
            purpose: ``confirm_email`` or ``reset_password``.
            token_sha256: Hex SHA-256 of the raw token. The raw token is not stored.
            expires_at: Moment the token stops working.
            now: Clock value used to mark older tokens used.
        """
        result = await self._session.execute(
            select(Credential).where(Credential.user_id == user_id)
        )
        credential = result.scalar_one()
        await self._session.execute(
            update(AuthToken)
            .where(
                AuthToken.credential_id == credential.id,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        self._session.add(
            AuthToken(
                id=uuid4(),
                credential_id=credential.id,
                purpose=purpose,
                token_sha256=token_sha256,
                expires_at=expires_at,
            )
        )
        await self._session.flush()

    async def consume_auth_token(
        self,
        *,
        token_sha256: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        """Mark a matching unused token used and return the participant id.

        A second call with the same digest returns None.

        Args:
            token_sha256: Hex SHA-256 of the presented token.
            purpose: Expected purpose.
            now: Clock value. Expired tokens are left unused and rejected.
        """
        result = await self._session.execute(
            update(AuthToken)
            .where(
                AuthToken.token_sha256 == token_sha256,
                AuthToken.purpose == purpose,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > now,
            )
            .values(used_at=now)
            .returning(AuthToken.credential_id)
        )
        credential_id = result.scalar_one_or_none()
        if credential_id is None:
            return None
        owner = await self._session.execute(
            select(Credential.user_id).where(Credential.id == credential_id)
        )
        return owner.scalar_one()

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None:
        """Set the confirmation timestamp on the credentials row.

        Args:
            user_id: Participant id.
            confirmed_at: Clock value.
        """
        await self._session.execute(
            update(Credential)
            .where(Credential.user_id == user_id)
            .values(email_confirmed_at=confirmed_at)
        )
        await self._session.flush()

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> None:
        """Replace the password hash. The password itself is not stored.

        Args:
            user_id: Participant id.
            password_hash: New PHC-encoded argon2id hash.
        """
        await self._session.execute(
            update(Credential)
            .where(Credential.user_id == user_id)
            .values(password_hash=password_hash)
        )
        await self._session.flush()

    async def list_consents(self, user_id: UUID) -> tuple[ConsentRecord, ...]:
        """Return consent rows for the participant, oldest grant first."""
        result = await self._session.execute(
            select(Consent).where(Consent.user_id == user_id).order_by(Consent.granted_at)
        )
        return tuple(_consent_record(row) for row in result.scalars())

    async def set_consent(
        self,
        *,
        user_id: UUID,
        consent_type: str,
        text_version: str,
        accepted: bool,
        now: datetime,
    ) -> ConsentRecord | None:
        """Grant or withdraw one consent. A declined optional consent with no row stays absent.

        Args:
            user_id: Participant id.
            consent_type: Catalogue type.
            text_version: Current text version.
            accepted: True grants or restores. False records withdrawal.
            now: Clock value for grant and withdrawal timestamps.
        """
        result = await self._session.execute(
            select(Consent)
            .where(Consent.user_id == user_id, Consent.consent_type == consent_type)
            .order_by(Consent.granted_at)
        )
        rows = list(result.scalars().all())
        if not accepted:
            active_rows = [row for row in rows if row.withdrawn_at is None]
            if not active_rows:
                return None
            for row in active_rows:
                row.withdrawn_at = now
            await self._session.flush()
            return _consent_record(active_rows[-1])
        active_current = next(
            (
                row
                for row in reversed(rows)
                if row.withdrawn_at is None and row.text_version == text_version
            ),
            None,
        )
        if active_current is not None:
            return _consent_record(active_current)
        for row in rows:
            if row.withdrawn_at is None:
                row.withdrawn_at = now
        row = Consent(
            id=uuid4(),
            user_id=user_id,
            consent_type=consent_type,
            text_version=text_version,
            granted_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return _consent_record(row)

    async def open_session(
        self,
        *,
        user_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> None:
        """Insert a session row. ``token_sha256`` is the digest of the cookie.

        Args:
            user_id: Signed-in participant.
            token_sha256: Hex SHA-256 of the raw cookie value.
            expires_at: Moment after which the cookie is rejected.
        """
        self._session.add(
            LoginSession(
                id=uuid4(),
                user_id=user_id,
                token_sha256=token_sha256,
                expires_at=expires_at,
            )
        )
        await self._session.flush()

    async def user_for_session(self, token_sha256: str, now: datetime) -> UserRecord | None:
        """Return the participant for a live digest, or None.

        An expired row is deleted so it cannot be reused.

        Args:
            token_sha256: Hex SHA-256 of the presented cookie.
            now: Current time. The caller owns the clock.
        """
        result = await self._session.execute(
            select(LoginSession).where(LoginSession.token_sha256 == token_sha256)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        if row.expires_at <= now:
            await self._session.delete(row)
            await self._session.flush()
            return None
        return await self.get_by_id(row.user_id)

    async def revoke_session(self, token_sha256: str) -> None:
        """Delete one session. A missing digest is ignored.

        Args:
            token_sha256: Hex SHA-256 of the cookie being logged out.
        """
        await self._session.execute(
            delete(LoginSession).where(LoginSession.token_sha256 == token_sha256)
        )
        await self._session.flush()

    async def revoke_sessions(self, user_id: UUID) -> None:
        """Delete every session for the participant.

        Args:
            user_id: Participant whose password just changed.
        """
        await self._session.execute(delete(LoginSession).where(LoginSession.user_id == user_id))
        await self._session.flush()

    async def credential_for_user(self, user_id: UUID) -> OwnCredential | None:
        """Return the owner's address and password hash, or None for a phrase account.

        Args:
            user_id: Signed-in participant.
        """
        result = await self._session.execute(
            select(Credential).where(Credential.user_id == user_id)
        )
        credential = result.scalar_one_or_none()
        if credential is None:
            return None
        return OwnCredential(email=credential.email, password_hash=credential.password_hash)

    async def count_live_sessions(self, user_id: UUID, now: datetime) -> int:
        """Count sessions that have not expired.

        Args:
            user_id: Signed-in participant.
            now: Current time. The caller owns the clock.
        """
        result = await self._session.execute(
            select(func.count())
            .select_from(LoginSession)
            .where(LoginSession.user_id == user_id, LoginSession.expires_at > now)
        )
        return int(result.scalar_one())

    async def revoke_other_sessions(self, user_id: UUID, keep_token_sha256: str) -> int:
        """Delete every session of the participant except ``keep_token_sha256``.

        Args:
            user_id: Signed-in participant.
            keep_token_sha256: Digest of the cookie that made the request.

        Returns:
            Number of deleted sessions.
        """
        result = await self._session.execute(
            delete(LoginSession)
            .where(
                LoginSession.user_id == user_id,
                LoginSession.token_sha256 != keep_token_sha256,
            )
            .returning(LoginSession.id)
        )
        removed = len(result.all())
        await self._session.flush()
        return removed

    async def delete_account(self, user_id: UUID) -> bool:
        """Delete the participant. Credentials, consents, lab rows, and journal rows cascade.

        Args:
            user_id: Participant id.
        """
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return False
        await self._session.delete(user)
        await self._session.flush()
        return True

    async def export_account(self, user_id: UUID) -> AccountExport | None:
        """Return the owner's copy, including the address and confirmed analytes.

        Args:
            user_id: Authenticated participant.
        """
        result = await self._session.execute(
            select(User)
            .options(
                selectinload(User.share_settings),
                selectinload(User.participant_profile),
                selectinload(User.profile_conditions),
            )
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            return None
        credential = await self._session.execute(
            select(Credential).where(Credential.user_id == user_id)
        )
        email_row = credential.scalar_one_or_none()
        consents = await self.list_consents(user_id)
        marker_rows = await self._session.execute(
            select(LabResult, Biomarker)
            .join(Biomarker, Biomarker.lab_result_id == LabResult.id)
            .where(LabResult.user_id == user_id)
            .order_by(LabResult.created_at, Biomarker.created_at)
        )
        markers = tuple(
            ExportedMarker(
                collected_at=lab.collected_at,
                lab_name=lab.lab_name,
                raw_name=marker.raw_name,
                loinc_code=marker.loinc_code,
                value=marker.value,
                unit=marker.unit,
                ref_low=marker.ref_low,
                ref_high=marker.ref_high,
                lab_flag=marker.lab_flag,
            )
            for lab, marker in marker_rows.all()
        )
        protocol_rows = await self._session.execute(
            select(ProtocolEntryRow)
            .where(ProtocolEntryRow.user_id == user_id)
            .order_by(ProtocolEntryRow.started_on.asc(), ProtocolEntryRow.created_at.asc())
        )
        protocol = tuple(
            ExportedProtocolEntry(
                kind=row.kind,
                title=row.title,
                dose=row.dose,
                started_on=row.started_on,
                ended_on=row.ended_on,
                note=row.note,
            )
            for row in protocol_rows.scalars().all()
        )
        is_public = user.share_settings.is_public if user.share_settings is not None else False
        profile_row = user.participant_profile
        profile = (
            None
            if profile_row is None
            else ParticipantProfile(
                sex_at_birth=cast(SexAtBirth | None, profile_row.sex_at_birth),
                year_of_birth=profile_row.year_of_birth,
                country=profile_row.country,
                height_cm=profile_row.height_cm,
                weight_kg=profile_row.weight_kg,
                smoking=cast(Smoking | None, profile_row.smoking),
                alcohol=cast(Alcohol | None, profile_row.alcohol),
                activity=cast(Activity | None, profile_row.activity),
                conditions=tuple(sorted(condition.code for condition in user.profile_conditions)),
                updated_at=profile_row.updated_at,
            )
        )
        return AccountExport(
            public_id=user.public_id,
            email=None if email_row is None else email_row.email,
            is_public=is_public,
            created_at=user.created_at,
            consents=consents,
            markers=markers,
            protocol=protocol,
            profile=profile,
        )


def _consent_record(row: Consent) -> ConsentRecord:
    """Map an ORM consent to a domain record."""
    return ConsentRecord(
        consent_type=row.consent_type,
        text_version=row.text_version,
        granted_at=row.granted_at,
        withdrawn_at=row.withdrawn_at,
    )
