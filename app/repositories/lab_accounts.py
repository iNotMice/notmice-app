"""Persistence for the separate laboratory identity and authentication boundary."""

from __future__ import annotations

from datetime import datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.lab_accounts import (
    LabLoginMaterial,
    LabOrganizationRecord,
    LabUserRecord,
    LabVerificationStatus,
)
from app.repositories.models import (
    LabAuthToken,
    LabSession,
    LabUser,
    Organization,
)


def _organization_record(row: Organization) -> LabOrganizationRecord:
    return LabOrganizationRecord(
        id=row.id,
        name=row.name,
        org_type=row.org_type,
        country=row.country,
        verification_status=cast(LabVerificationStatus, row.verification_status),
        dua_version=row.dua_version,
        dua_accepted_at=row.dua_accepted_at,
        verified_at=row.verified_at,
        verification_reviewed_at=row.verification_reviewed_at,
        verified_by=row.verified_by,
        verification_evidence=row.verification_evidence,
    )


def _user_record(row: LabUser, organization: Organization) -> LabUserRecord:
    return LabUserRecord(
        id=row.id,
        organization_id=row.organization_id,
        email=row.email,
        role=row.role,
        email_confirmed_at=row.email_confirmed_at,
        organization=_organization_record(organization),
    )


class LabAccountRepository:
    """Store lab accounts, their auth material, and organization access state."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_organization_owner(
        self,
        *,
        name: str,
        org_type: str,
        country: str,
        email: str,
        password_hash: str,
    ) -> LabUserRecord:
        """Create a pending organization and its first owner in one transaction."""
        organization = Organization(
            id=uuid4(),
            name=name,
            org_type=org_type,
            country=country,
            verification_status="pending",
        )
        user = LabUser(
            id=uuid4(),
            organization_id=organization.id,
            email=email,
            password_hash=password_hash,
            role="owner",
        )
        self._session.add_all((organization, user))
        await self._session.flush()
        return _user_record(user, organization)

    async def login_material(self, email: str) -> LabLoginMaterial | None:
        """Load password material by normalized email."""
        result = await self._session.execute(select(LabUser).where(LabUser.email == email))
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return LabLoginMaterial(
            user_id=row.id,
            password_hash=row.password_hash,
            email_confirmed_at=row.email_confirmed_at,
        )

    async def user_by_id(self, user_id: UUID) -> LabUserRecord | None:
        """Load a lab user with its organization status."""
        result = await self._session.execute(
            select(LabUser, Organization)
            .join(Organization, LabUser.organization_id == Organization.id)
            .where(LabUser.id == user_id)
        )
        row = result.one_or_none()
        return None if row is None else _user_record(row[0], row[1])

    async def save_auth_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_sha256: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        """Retire previous unused tokens of the same purpose and store the new digest."""
        await self._session.execute(
            update(LabAuthToken)
            .where(LabAuthToken.lab_user_id == user_id)
            .where(LabAuthToken.purpose == purpose)
            .where(LabAuthToken.used_at.is_(None))
            .values(used_at=now)
        )
        self._session.add(
            LabAuthToken(
                id=uuid4(),
                lab_user_id=user_id,
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
        """Atomically consume one unexpired token digest."""
        result = await self._session.execute(
            select(LabAuthToken)
            .where(LabAuthToken.token_sha256 == token_sha256)
            .where(LabAuthToken.purpose == purpose)
            .where(LabAuthToken.used_at.is_(None))
            .where(LabAuthToken.expires_at > now)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.used_at = now
        await self._session.flush()
        return row.lab_user_id

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None:
        """Mark a laboratory email address as confirmed."""
        await self._session.execute(
            update(LabUser).where(LabUser.id == user_id).values(email_confirmed_at=confirmed_at)
        )

    async def open_session(
        self,
        *,
        user_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> None:
        """Persist a lab session digest, never the raw cookie token."""
        self._session.add(
            LabSession(
                id=uuid4(),
                lab_user_id=user_id,
                token_sha256=token_sha256,
                expires_at=expires_at,
            )
        )
        await self._session.flush()

    async def user_for_session(self, token_sha256: str, now: datetime) -> LabUserRecord | None:
        """Resolve a live session digest to its lab user and organization."""
        result = await self._session.execute(
            select(LabUser, Organization)
            .join(LabSession, LabSession.lab_user_id == LabUser.id)
            .join(Organization, Organization.id == LabUser.organization_id)
            .where(LabSession.token_sha256 == token_sha256)
            .where(LabSession.expires_at > now)
        )
        row = result.one_or_none()
        return None if row is None else _user_record(row[0], row[1])

    async def revoke_session(self, token_sha256: str) -> None:
        """Remove one lab session digest."""
        await self._session.execute(
            delete(LabSession).where(LabSession.token_sha256 == token_sha256)
        )

    async def revoke_sessions(self, user_id: UUID) -> None:
        """Expire all lab sessions for one user."""
        await self._session.execute(delete(LabSession).where(LabSession.lab_user_id == user_id))

    async def accept_dua(
        self,
        organization_id: UUID,
        *,
        version: str,
        accepted_at: datetime,
    ) -> bool:
        """Record the current DUA acceptance for a verified organization."""
        result = await self._session.execute(
            update(Organization)
            .where(Organization.id == organization_id)
            .where(Organization.verification_status == "verified")
            .values(dua_version=version, dua_accepted_at=accepted_at)
            .returning(Organization.id)
        )
        return result.scalar_one_or_none() is not None

    async def verify_organization(
        self,
        organization_id: UUID,
        *,
        status: str,
        operator: str,
        evidence: str,
        verified_at: datetime,
    ) -> bool:
        """Set organization verification state and retain operator evidence."""
        values: dict[str, object] = {
            "verification_status": status,
            "verified_at": verified_at if status == "verified" else None,
            "verification_reviewed_at": verified_at,
            "verified_by": operator,
            "verification_evidence": evidence,
        }
        if status != "verified":
            values.update(dua_version=None, dua_accepted_at=None)
        result = await self._session.execute(
            update(Organization)
            .where(Organization.id == organization_id)
            .values(**values)
            .returning(Organization.id)
        )
        return result.scalar_one_or_none() is not None
