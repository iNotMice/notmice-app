"""Laboratory registration, isolated sessions, manual verification, and DUA gates."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.lab_accounts import LAB_SESSION_COOKIE_NAME
from app.core.deps import get_lab_account_service
from app.core.security import auth_token_digest
from app.domain.lab_accounts import (
    LabAuthTokenError,
    LabDuaUnavailableError,
    LabInvalidCredentialsError,
    LabLoginMaterial,
    LabOrganizationAccessError,
    LabOrganizationRecord,
    LabUserRecord,
    LabVerificationStatus,
)
from app.main import create_app
from app.services.lab_accounts import LabAccountService
from app.services.mailer import CapturingMailer


class FakePasswordHasher:
    """Deterministic test-only password checker."""

    def hash_password(self, password: str) -> str:
        return f"hash:{password}"

    def verify(self, password_hash: str, password: str) -> bool:
        return password_hash == f"hash:{password}"

    def verify_dummy(self, password: str) -> None:
        assert password


class InMemoryLabAccountStore:
    """Isolated in-memory persistence matching the lab identity contract."""

    def __init__(self) -> None:
        self.users: dict[UUID, LabUserRecord] = {}
        self.passwords: dict[str, LabLoginMaterial] = {}
        self.tokens: dict[str, tuple[UUID, str, datetime, bool]] = {}
        self.sessions: dict[str, tuple[UUID, datetime]] = {}

    async def create_organization_owner(
        self,
        *,
        name: str,
        org_type: str,
        country: str,
        email: str,
        password_hash: str,
    ) -> LabUserRecord:
        organization = LabOrganizationRecord(
            id=uuid4(),
            name=name,
            org_type=org_type,
            country=country,
            verification_status="pending",
            dua_version=None,
            dua_accepted_at=None,
            verified_at=None,
            verification_reviewed_at=None,
            verified_by=None,
            verification_evidence=None,
        )
        user = LabUserRecord(
            id=uuid4(),
            organization_id=organization.id,
            email=email,
            role="owner",
            email_confirmed_at=None,
            organization=organization,
        )
        self.users[user.id] = user
        self.passwords[email] = LabLoginMaterial(
            user_id=user.id,
            password_hash=password_hash,
            email_confirmed_at=None,
        )
        return user

    async def login_material(self, email: str) -> LabLoginMaterial | None:
        return self.passwords.get(email)

    async def user_by_id(self, user_id: UUID) -> LabUserRecord | None:
        return self.users.get(user_id)

    async def save_auth_token(
        self,
        *,
        user_id: UUID,
        purpose: str,
        token_sha256: str,
        expires_at: datetime,
        now: datetime,
    ) -> None:
        del now
        self.tokens[token_sha256] = (user_id, purpose, expires_at, False)

    async def consume_auth_token(
        self,
        *,
        token_sha256: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        row = self.tokens.get(token_sha256)
        if row is None or row[1] != purpose or row[2] <= now or row[3]:
            return None
        self.tokens[token_sha256] = (row[0], row[1], row[2], True)
        return row[0]

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None:
        user = self.users[user_id]
        self.users[user_id] = replace(user, email_confirmed_at=confirmed_at)
        self.passwords[user.email] = replace(
            self.passwords[user.email],
            email_confirmed_at=confirmed_at,
        )

    async def open_session(
        self,
        *,
        user_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> None:
        self.sessions[token_sha256] = (user_id, expires_at)

    async def user_for_session(self, token_sha256: str, now: datetime) -> LabUserRecord | None:
        row = self.sessions.get(token_sha256)
        if row is None or row[1] <= now:
            return None
        return self.users.get(row[0])

    async def revoke_session(self, token_sha256: str) -> None:
        self.sessions.pop(token_sha256, None)

    async def accept_dua(
        self,
        organization_id: UUID,
        *,
        version: str,
        accepted_at: datetime,
    ) -> bool:
        for user_id, user in self.users.items():
            if user.organization_id == organization_id:
                organization = replace(
                    user.organization,
                    dua_version=version,
                    dua_accepted_at=accepted_at,
                )
                self.users[user_id] = replace(user, organization=organization)
                return True
        return False

    async def verify_organization(
        self,
        organization_id: UUID,
        *,
        status: LabVerificationStatus,
        operator: str,
        evidence: str,
        verified_at: datetime,
    ) -> bool:
        for user_id, user in self.users.items():
            if user.organization_id == organization_id:
                organization = replace(
                    user.organization,
                    verification_status=status,
                    verified_at=verified_at if status == "verified" else None,
                    verification_reviewed_at=verified_at,
                    verified_by=operator,
                    verification_evidence=evidence,
                    dua_version=None if status != "verified" else user.organization.dua_version,
                    dua_accepted_at=(
                        None if status != "verified" else user.organization.dua_accepted_at
                    ),
                )
                self.users[user_id] = replace(user, organization=organization)
                return True
        return False


def _service() -> tuple[LabAccountService, InMemoryLabAccountStore, CapturingMailer]:
    store = InMemoryLabAccountStore()
    mailer = CapturingMailer()
    service = LabAccountService(
        store=store,
        passwords=FakePasswordHasher(),
        mailer=mailer,
        app_url="https://notmice.example",
    )
    return service, store, mailer


def _token(mailer: CapturingMailer) -> str:
    link = mailer.sent[-1].body.strip().splitlines()[-1]
    return link.split("token=", maxsplit=1)[1]


@pytest.mark.asyncio
async def test_registration_confirm_and_lab_login_are_separate_from_participants() -> None:
    """New lab registrations remain pending and use their own token/session storage."""
    service, store, mailer = _service()
    await service.register(
        name="  Example   Research Lab ",
        org_type="laboratory",
        country="DE",
        email="Lab.Owner@example.com",
        password="correct-horse-battery",
    )
    assert len(store.users) == 1
    user = next(iter(store.users.values()))
    assert user.email == "lab.owner@example.com"
    assert user.organization.name == "Example Research Lab"
    assert user.organization.verification_status == "pending"
    assert user.email_confirmed_at is None
    assert _token(mailer) not in store.tokens

    with pytest.raises(LabInvalidCredentialsError):
        await service.login("lab.owner@example.com", "correct-horse-battery")

    confirmed, cookie = await service.confirm_email(_token(mailer))
    assert confirmed.email_confirmed_at is not None
    assert confirmed.organization.verification_status == "pending"
    digest = auth_token_digest(cookie)
    assert digest is not None
    assert digest in store.sessions
    assert await service.authenticate(cookie) == confirmed
    with pytest.raises(LabAuthTokenError):
        await service.confirm_email(_token(mailer))


@pytest.mark.asyncio
async def test_manual_verification_and_current_dua_are_both_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pending organizations and absent legal DUA versions fail closed."""
    service, store, mailer = _service()
    await service.register(
        name="Example University",
        org_type="university",
        country="US",
        email="owner@example.com",
        password="correct-horse-battery",
    )
    user, _cookie = await service.confirm_email(_token(mailer))
    with pytest.raises(LabOrganizationAccessError):
        await service.require_verified_dua(user)

    verified_at = datetime.now(UTC)
    assert await store.verify_organization(
        user.organization_id,
        status="verified",
        operator="operator-1",
        evidence="Registry checked",
        verified_at=verified_at,
    )
    verified = await store.user_by_id(user.id)
    assert verified is not None
    with pytest.raises(LabDuaUnavailableError):
        await service.accept_current_dua(verified)

    monkeypatch.setattr("app.services.lab_accounts.CURRENT_DUA_VERSION", "test-dua-v1")
    accepted = await service.accept_current_dua(verified)
    assert accepted.organization.dua_version == "test-dua-v1"
    assert await service.require_verified_dua(accepted) == accepted

    assert await store.verify_organization(
        user.organization_id,
        status="rejected",
        operator="operator-1",
        evidence="Verification withdrawn",
        verified_at=datetime.now(UTC),
    )
    rejected = await store.user_by_id(user.id)
    assert rejected is not None
    with pytest.raises(LabOrganizationAccessError):
        await service.require_verified_dua(rejected)


@pytest.mark.asyncio
async def test_lab_me_route_uses_only_lab_session_cookie() -> None:
    """A participant session is not accepted by the laboratory identity endpoint."""
    service, _store, mailer = _service()

    app: FastAPI = create_app()
    async def override_service() -> LabAccountService:
        return service

    app.dependency_overrides[get_lab_account_service] = override_service
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        registered = await client.post(
            "/api/v1/lab/register",
            json={
                "organization_name": "Example Institute",
                "organization_type": "research_institute",
                "country": "GB",
                "email": "owner@example.com",
                "password": "correct-horse-battery",
            },
        )
        assert registered.status_code == 202
        token = _token(mailer)
        link_page = await client.get("/api/v1/lab/confirm", params={"token": token})
        assert link_page.status_code == 200
        assert token in link_page.text
        assert "no-store" in link_page.headers["cache-control"]
        assert "frame-ancestors 'none'" in link_page.headers["content-security-policy"]
        confirmed = await client.post("/api/v1/lab/confirm", json={"token": token})
        assert confirmed.status_code == 200
        assert LAB_SESSION_COOKIE_NAME in confirmed.cookies
        lab_cookie = confirmed.cookies[LAB_SESSION_COOKIE_NAME]
        client.cookies.set(LAB_SESSION_COOKIE_NAME, lab_cookie)
        response = await client.get("/api/v1/lab/me")
        assert response.status_code == 200
        assert response.json()["organization"]["verification_status"] == "pending"
        assert "verification_evidence" not in response.json()["organization"]
        blocked_dua = await client.post(
            "/api/v1/lab/dua/accept",
            json={"accepted": True},
        )
    assert blocked_dua.status_code == 403
    assert confirmed.json()["email"] == "owner@example.com"
    assert confirmed.json()["organization"]["dua_version"] is None

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"notmice_session": lab_cookie},
    ) as participant_cookie_client:
        unauthorized = await participant_cookie_client.get("/api/v1/lab/me")
    assert unauthorized.status_code == 401
    assert LAB_SESSION_COOKIE_NAME == "notmice_lab_session"
    assert lab_cookie not in response.text
