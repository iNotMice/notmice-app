"""Account service and HTTP tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.accounts import SESSION_COOKIE_NAME
from app.core.config import get_settings
from app.core.deps import (
    get_account_identity_rate_limiter,
    get_account_rate_limiter,
    get_account_service,
)
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import (
    Argon2SeedHasher,
    auth_token_digest,
    generate_mnemonic,
    is_valid_mnemonic,
)
from app.domain.accounts import (
    AccountExport,
    ConsentRecord,
    EmailLogin,
    ExportedProtocolEntry,
    InvalidCredentialsError,
    InvalidMnemonicError,
    UnauthenticatedError,
    UserRecord,
)
from app.main import create_app
from app.services.accounts import AccountService


class _MemoryCredential:
    def __init__(self, user_id: UUID, email: str, password_hash: str) -> None:
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.email_confirmed_at: datetime | None = None


class _MemoryToken:
    def __init__(
        self, user_id: UUID, purpose: str, token_sha256: str, expires_at: datetime
    ) -> None:
        self.user_id = user_id
        self.purpose = purpose
        self.token_sha256 = token_sha256
        self.expires_at = expires_at
        self.used_at: datetime | None = None


class _MemorySession:
    def __init__(self, user_id: UUID, expires_at: datetime) -> None:
        self.user_id = user_id
        self.expires_at = expires_at


class InMemoryUserStore:
    """Process-local stand-in for UserRepository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, UserRecord] = {}
        self._by_public: dict[str, UUID] = {}
        self._by_hash: dict[str, UUID] = {}
        self._credentials: dict[str, _MemoryCredential] = {}
        self._credential_by_user: dict[UUID, _MemoryCredential] = {}
        self._tokens: list[_MemoryToken] = []
        self._consents: dict[UUID, list[ConsentRecord]] = {}
        self._sessions: dict[str, _MemorySession] = {}
        self.exported_protocol: dict[UUID, tuple[ExportedProtocolEntry, ...]] = {}

    async def create(self, *, public_id: str, seed_phrase_hash: str) -> UserRecord:
        user_id = uuid4()
        record = UserRecord(
            id=user_id,
            public_id=public_id,
            is_public=False,
            created_at=datetime.now(UTC),
        )
        self._by_id[user_id] = record
        self._by_public[public_id] = user_id
        self._by_hash[seed_phrase_hash] = user_id
        return record

    async def get_by_id(self, user_id: UUID) -> UserRecord | None:
        return self._by_id.get(user_id)

    async def get_by_public_id(self, public_id: str) -> UserRecord | None:
        user_id = self._by_public.get(public_id)
        return self._by_id.get(user_id) if user_id is not None else None

    async def get_by_seed_phrase_hash(self, seed_phrase_hash: str) -> UserRecord | None:
        user_id = self._by_hash.get(seed_phrase_hash)
        return self._by_id.get(user_id) if user_id is not None else None

    async def set_is_public(self, user_id: UUID, is_public: bool) -> UserRecord | None:
        current = self._by_id.get(user_id)
        if current is None:
            return None
        updated = UserRecord(
            id=current.id,
            public_id=current.public_id,
            is_public=is_public,
            created_at=current.created_at,
        )
        self._by_id[user_id] = updated
        return updated

    async def create_email_account(
        self,
        *,
        public_id: str,
        email: str,
        password_hash: str,
        consents: tuple[tuple[str, str], ...],
        granted_at: datetime,
    ) -> UserRecord:
        user_id = uuid4()
        record = UserRecord(
            id=user_id,
            public_id=public_id,
            is_public=False,
            created_at=granted_at,
        )
        credential = _MemoryCredential(user_id, email, password_hash)
        self._by_id[user_id] = record
        self._by_public[public_id] = user_id
        self._credentials[email] = credential
        self._credential_by_user[user_id] = credential
        self._consents[user_id] = [
            ConsentRecord(
                consent_type=consent_type,
                text_version=text_version,
                granted_at=granted_at,
                withdrawn_at=None,
            )
            for consent_type, text_version in consents
        ]
        return record

    async def find_email(self, email: str) -> EmailLogin | None:
        credential = self._credentials.get(email)
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
        for token in self._tokens:
            if token.user_id == user_id and token.purpose == purpose and token.used_at is None:
                token.used_at = now
        self._tokens.append(_MemoryToken(user_id, purpose, token_sha256, expires_at))

    async def consume_auth_token(
        self,
        *,
        token_sha256: str,
        purpose: str,
        now: datetime,
    ) -> UUID | None:
        for token in self._tokens:
            if (
                token.token_sha256 == token_sha256
                and token.purpose == purpose
                and token.used_at is None
                and token.expires_at > now
            ):
                token.used_at = now
                return token.user_id
        return None

    async def mark_email_confirmed(self, user_id: UUID, confirmed_at: datetime) -> None:
        credential = self._credential_by_user[user_id]
        credential.email_confirmed_at = confirmed_at

    async def set_password_hash(self, user_id: UUID, password_hash: str) -> None:
        self._credential_by_user[user_id].password_hash = password_hash

    async def list_consents(self, user_id: UUID) -> tuple[ConsentRecord, ...]:
        return tuple(self._consents.get(user_id, []))

    async def set_consent(
        self,
        *,
        user_id: UUID,
        consent_type: str,
        text_version: str,
        accepted: bool,
        now: datetime,
    ) -> ConsentRecord | None:
        rows = self._consents.setdefault(user_id, [])
        for index, row in enumerate(rows):
            if row.consent_type != consent_type:
                continue
            if not accepted:
                updated = ConsentRecord(
                    consent_type=row.consent_type,
                    text_version=row.text_version,
                    granted_at=row.granted_at,
                    withdrawn_at=now,
                )
            else:
                updated = ConsentRecord(
                    consent_type=consent_type,
                    text_version=text_version,
                    granted_at=now,
                    withdrawn_at=None,
                )
            rows[index] = updated
            return updated
        if not accepted:
            return None
        created = ConsentRecord(
            consent_type=consent_type,
            text_version=text_version,
            granted_at=now,
            withdrawn_at=None,
        )
        rows.append(created)
        return created

    async def delete_account(self, user_id: UUID) -> bool:
        current = self._by_id.pop(user_id, None)
        if current is None:
            return False
        self._by_public.pop(current.public_id, None)
        self._by_hash = {
            phrase_hash: owner for phrase_hash, owner in self._by_hash.items() if owner != user_id
        }
        credential = self._credential_by_user.pop(user_id, None)
        if credential is not None:
            self._credentials.pop(credential.email, None)
        self._tokens = [token for token in self._tokens if token.user_id != user_id]
        self._consents.pop(user_id, None)
        self._sessions = {
            digest: row for digest, row in self._sessions.items() if row.user_id != user_id
        }
        self.exported_protocol.pop(user_id, None)
        return True

    async def export_account(self, user_id: UUID) -> AccountExport | None:
        current = self._by_id.get(user_id)
        if current is None:
            return None
        credential = self._credential_by_user.get(user_id)
        return AccountExport(
            public_id=current.public_id,
            email=None if credential is None else credential.email,
            is_public=current.is_public,
            created_at=current.created_at,
            consents=tuple(self._consents.get(user_id, [])),
            markers=(),
            protocol=tuple(self.exported_protocol.get(user_id, ())),
        )

    async def open_session(
        self,
        *,
        user_id: UUID,
        token_sha256: str,
        expires_at: datetime,
    ) -> None:
        self._sessions[token_sha256] = _MemorySession(user_id, expires_at)

    async def user_for_session(self, token_sha256: str, now: datetime) -> UserRecord | None:
        row = self._sessions.get(token_sha256)
        if row is None:
            return None
        if row.expires_at <= now:
            self._sessions.pop(token_sha256, None)
            return None
        return self._by_id.get(row.user_id)

    async def revoke_session(self, token_sha256: str) -> None:
        self._sessions.pop(token_sha256, None)

    async def revoke_sessions(self, user_id: UUID) -> None:
        self._sessions = {
            digest: row for digest, row in self._sessions.items() if row.user_id != user_id
        }


def _service(store: InMemoryUserStore | None = None) -> tuple[AccountService, InMemoryUserStore]:
    users = store if store is not None else InMemoryUserStore()
    service = AccountService(
        users=users,
        hasher=Argon2SeedHasher("test-pepper-secret-key-32-bytes!!"),
    )
    return service, users


def test_in_memory_store_keeps_hash_not_phrase() -> None:
    """The store API accepts only a hash field name, never a mnemonic field."""
    assert "mnemonic" not in InMemoryUserStore.create.__code__.co_varnames


async def test_create_returns_valid_bip39_and_private_share() -> None:
    """New accounts get a real 12-word phrase and default-private sharing."""
    service, _users = _service()
    created = await service.create()
    words = created.mnemonic.split(" ")
    assert len(words) == 12
    assert is_valid_mnemonic(created.mnemonic) is True
    assert created.user.is_public is False
    assert created.user.public_id.startswith("nm")
    assert created.session_token


async def test_create_does_not_persist_mnemonic_on_user_record() -> None:
    """UserRecord has no mnemonic attribute; the phrase is only on CreatedAccount."""
    service, _users = _service()
    created = await service.create()
    assert not hasattr(created.user, "mnemonic")
    assert created.mnemonic not in created.user.public_id
    assert created.mnemonic not in created.session_token


async def test_login_with_same_phrase_succeeds() -> None:
    """DoD: create, then authenticate with the same phrase."""
    service, _users = _service()
    created = await service.create()
    session = await service.login(created.mnemonic)
    assert session.user.public_id == created.user.public_id


async def test_login_accepts_messy_whitespace() -> None:
    """Pasted phrases with extra spaces still log in."""
    service, _users = _service()
    created = await service.create()
    messy = "  " + "  ".join(created.mnemonic.split(" ")) + "\n"
    session = await service.login(messy)
    assert session.user.id == created.user.id


async def test_login_rejects_unknown_valid_mnemonic() -> None:
    """A well-formed phrase that was never registered is 401-class."""
    service, _users = _service()
    with pytest.raises(InvalidCredentialsError):
        await service.login(generate_mnemonic())


async def test_login_rejects_ui_stub_phrase() -> None:
    """The former INITIAL_MNEMONIC words are not a valid BIP-39 phrase."""
    service, _users = _service()
    stub = (
        "quantum cellular longevity telomere biomarker hepatic "
        "hazard matrix isolate gompertz cipher sovereign"
    )
    with pytest.raises(InvalidMnemonicError):
        await service.login(stub)


async def test_set_public_toggles_share_settings() -> None:
    """The publicity toggle updates the user record."""
    service, _users = _service()
    created = await service.create()
    updated = await service.set_public(created.user.id, True)
    assert updated.is_public is True
    restored = await service.set_public(created.user.id, False)
    assert restored.is_public is False


async def test_authenticate_requires_token() -> None:
    """A missing session cookie is unauthenticated."""
    service, _users = _service()
    with pytest.raises(UnauthenticatedError):
        await service.authenticate(None)


async def test_session_stores_the_digest_and_logout_revokes_it() -> None:
    """The store keeps SHA-256 only. Logout makes that cookie unusable."""
    service, users = _service()
    created = await service.create()
    digest = auth_token_digest(created.session_token)
    assert digest is not None
    assert created.session_token not in users._sessions
    assert digest in users._sessions
    assert (await service.authenticate(created.session_token)).id == created.user.id
    await service.logout(created.session_token)
    with pytest.raises(UnauthenticatedError):
        await service.authenticate(created.session_token)


async def test_expired_session_is_rejected() -> None:
    """A cookie past its expiry does not open the account."""
    service, _users = _service()
    start = datetime(2026, 9, 28, tzinfo=UTC)
    service._now = lambda: start
    service._session_ttl = timedelta(seconds=30)
    created = await service.create()
    service._now = lambda: start + timedelta(seconds=31)
    with pytest.raises(UnauthenticatedError):
        await service.authenticate(created.session_token)


def _override_app(service: AccountService) -> FastAPI:
    application = create_app()

    async def override() -> AccountService:
        return service

    application.dependency_overrides[get_account_service] = override
    application.dependency_overrides[get_account_rate_limiter] = lambda: SlidingWindowRateLimiter(
        limit=1000,
        window_seconds=60,
    )
    application.dependency_overrides[get_account_identity_rate_limiter] = lambda: (
        SlidingWindowRateLimiter(limit=1000, window_seconds=60)
    )
    return application


async def test_post_accounts_without_email_is_rejected() -> None:
    """New registration requires an email. An empty body is not a phrase account."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/accounts", json={})
    assert response.status_code == 422


async def test_post_accounts_rejects_phone() -> None:
    """Registration does not accept a phone field."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts",
            json={
                "email": "someone@example.com",
                "password": "correct-horse-battery",
                "phone": "1",
            },
        )
    assert response.status_code == 422


async def test_create_logout_login_http_flow() -> None:
    """DoD HTTP path: a phrase account can log out and log in with the same phrase."""
    service, _users = _service()
    application = _override_app(service)
    created = await service.create()
    mnemonic = created.mnemonic
    public_id = created.user.public_id
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        client.cookies.set(SESSION_COOKIE_NAME, created.session_token)
        me = await client.get("/api/v1/accounts/me")
        assert me.status_code == 200
        assert me.json()["public_id"] == public_id
        assert "mnemonic" not in me.json()
        assert "access_token" not in me.json()

        logged_out = await client.post("/api/v1/accounts/logout")
        assert logged_out.status_code == 204
        signed_out = await client.get("/api/v1/accounts/me")
        assert signed_out.status_code == 401

        login = await client.post("/api/v1/accounts/login", json={"mnemonic": mnemonic})
        assert login.status_code == 200
        assert login.json()["public_id"] == public_id
        assert "mnemonic" not in login.json()
        assert "access_token" not in login.json()
        set_cookie = login.headers["set-cookie"]
        flags = {part.strip().lower() for part in set_cookie.split(";")[1:]}
        assert set_cookie.lower().startswith(f"{SESSION_COOKIE_NAME}=")
        assert "httponly" in flags
        assert "samesite=lax" in flags
        assert ("secure" in flags) is get_settings().session_cookie_secure

        me_again = await client.get("/api/v1/accounts/me")
        assert me_again.status_code == 200
        assert me_again.json()["public_id"] == public_id


async def test_login_wrong_phrase_is_401() -> None:
    """A valid unused mnemonic does not open someone else's account."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts/login",
            json={"mnemonic": generate_mnemonic()},
        )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid recovery phrase"


@pytest.mark.asyncio
async def test_login_hides_whether_the_phrase_checksum_passed() -> None:
    """A broken phrase and a valid unknown phrase return the same status and detail."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        broken = await client.post(
            "/api/v1/accounts/login",
            json={"mnemonic": "not a recovery phrase"},
        )
        unknown = await client.post(
            "/api/v1/accounts/login",
            json={"mnemonic": generate_mnemonic()},
        )
    assert broken.status_code == 401
    assert unknown.status_code == 401
    assert broken.json()["detail"] == unknown.json()["detail"] == "Invalid recovery phrase"


@pytest.mark.asyncio
async def test_account_create_is_rate_limited() -> None:
    """Repeated account creation from one address is refused."""
    service, _users = _service()
    application = _override_app(service)
    limiter = SlidingWindowRateLimiter(limit=2, window_seconds=60)
    application.dependency_overrides[get_account_rate_limiter] = lambda: limiter
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        body = {
            "password": "correct-horse-battery",
            "consents": [{"type": "health_data", "version": "2026-09-28", "accepted": True}],
        }
        first = await client.post("/api/v1/accounts", json={"email": "one@example.com", **body})
        second = await client.post("/api/v1/accounts", json={"email": "two@example.com", **body})
        third = await client.post("/api/v1/accounts", json={"email": "three@example.com", **body})
    assert first.status_code == 202
    assert second.status_code == 202
    assert third.status_code == 429
    assert third.json()["detail"] == "Rate limit exceeded"


async def test_me_without_token_is_401() -> None:
    """Protected routes reject missing credentials."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/accounts/me")
    assert response.status_code == 401


async def test_share_toggle_http() -> None:
    """PATCH /me/share persists is_public on the account."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await service.create()
        client.cookies.set(SESSION_COOKIE_NAME, created.session_token)
        public = await client.patch(
            "/api/v1/accounts/me/share",
            json={"is_public": True},
        )
        assert public.status_code == 200
        assert public.json()["is_public"] is True
        me = await client.get("/api/v1/accounts/me")
        assert me.json()["is_public"] is True


async def test_accounts_against_postgres() -> None:
    """Register, confirm from the dev mail log, and sign in when Postgres is up."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.ext.asyncio import create_async_engine
    from structlog.testing import capture_logs

    from app.core.config import get_settings

    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (OSError, OperationalError):
        pytest.skip("PostgreSQL is not available")
    finally:
        await engine.dispose()

    email = f"postgres-{uuid4().hex}@example.com"
    payload = {
        "email": email,
        "password": "correct-horse-battery",
        "consents": [{"type": "health_data", "version": "2026-09-28", "accepted": True}],
    }
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with capture_logs() as logs:
            created = await client.post("/api/v1/accounts", json=payload)
        assert created.status_code == 202
        assert created.json() == {"status": "accepted"}
        again = await client.post("/api/v1/accounts", json=payload)
        assert again.status_code == 202
        assert again.json() == created.json()
        blocked = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": email, "password": "correct-horse-battery"},
        )
        assert blocked.status_code == 401
        body = next(row["body"] for row in logs if row.get("event") == "auth_mail_dev")
        token = str(body).split("confirm=", maxsplit=1)[1].split()[0]
        confirmed = await client.post("/api/v1/accounts/confirm", json={"token": token})
        assert confirmed.status_code == 200
        assert "mnemonic" not in confirmed.json()
