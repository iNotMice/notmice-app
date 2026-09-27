"""Account service and HTTP tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_account_rate_limiter, get_account_service
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import (
    Argon2SeedHasher,
    JwtTokenIssuer,
    generate_mnemonic,
    is_valid_mnemonic,
)
from app.domain.accounts import (
    InvalidCredentialsError,
    InvalidMnemonicError,
    UnauthenticatedError,
    UserRecord,
)
from app.main import create_app
from app.services.accounts import AccountService


class InMemoryUserStore:
    """Process-local stand-in for UserRepository."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, UserRecord] = {}
        self._by_public: dict[str, UUID] = {}
        self._by_hash: dict[str, UUID] = {}

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


def _service(store: InMemoryUserStore | None = None) -> tuple[AccountService, InMemoryUserStore]:
    users = store if store is not None else InMemoryUserStore()
    service = AccountService(
        users=users,
        hasher=Argon2SeedHasher("test-pepper-secret-key-32-bytes!!"),
        tokens=JwtTokenIssuer("test-jwt-secret-key-32-bytes-min!", ttl_seconds=3600),
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
    assert created.access_token


async def test_create_does_not_persist_mnemonic_on_user_record() -> None:
    """UserRecord has no mnemonic attribute; the phrase is only on CreatedAccount."""
    service, _users = _service()
    created = await service.create()
    assert not hasattr(created.user, "mnemonic")
    assert created.mnemonic not in created.user.public_id
    assert created.mnemonic not in created.access_token


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
    """Missing bearer tokens are unauthenticated."""
    service, _users = _service()
    with pytest.raises(UnauthenticatedError):
        await service.authenticate(None)


def _override_app(service: AccountService) -> FastAPI:
    application = create_app()

    async def override() -> AccountService:
        return service

    application.dependency_overrides[get_account_service] = override
    application.dependency_overrides[get_account_rate_limiter] = lambda: SlidingWindowRateLimiter(
        limit=1000,
        window_seconds=60,
    )
    return application


async def test_post_accounts_returns_mnemonic_once() -> None:
    """POST /api/v1/accounts is 201 with a BIP-39 phrase and a token."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/v1/accounts", json={})
    assert response.status_code == 201
    body = response.json()
    assert is_valid_mnemonic(body["mnemonic"]) is True
    assert body["token_type"] == "bearer"
    assert body["is_public"] is False
    assert "seed_phrase_hash" not in body
    assert "$argon2id$" not in response.text


async def test_post_accounts_rejects_email() -> None:
    """Registration does not accept an email field."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts",
            json={"email": "someone@example.com"},
        )
    assert response.status_code == 422


async def test_create_logout_login_http_flow() -> None:
    """DoD HTTP path: create account, logout, login with the same phrase."""
    service, _users = _service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/accounts", json={})
        assert created.status_code == 201
        mnemonic = created.json()["mnemonic"]
        public_id = created.json()["public_id"]
        token = created.json()["access_token"]

        me = await client.get(
            "/api/v1/accounts/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me.status_code == 200
        assert me.json()["public_id"] == public_id
        assert "mnemonic" not in me.json()

        logged_out = await client.post(
            "/api/v1/accounts/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert logged_out.status_code == 204

        login = await client.post("/api/v1/accounts/login", json={"mnemonic": mnemonic})
        assert login.status_code == 200
        assert login.json()["public_id"] == public_id
        assert "mnemonic" not in login.json()
        new_token = login.json()["access_token"]

        me_again = await client.get(
            "/api/v1/accounts/me",
            headers={"Authorization": f"Bearer {new_token}"},
        )
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
        first = await client.post("/api/v1/accounts", json={})
        second = await client.post("/api/v1/accounts", json={})
        third = await client.post("/api/v1/accounts", json={})
    assert first.status_code == 201
    assert second.status_code == 201
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
        created = await client.post("/api/v1/accounts", json={})
        token = created.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        public = await client.patch(
            "/api/v1/accounts/me/share",
            headers=headers,
            json={"is_public": True},
        )
        assert public.status_code == 200
        assert public.json()["is_public"] is True
        me = await client.get("/api/v1/accounts/me", headers=headers)
        assert me.json()["is_public"] is True


async def test_accounts_against_postgres() -> None:
    """Create → logout → login against a real database when Postgres is up."""
    from sqlalchemy import text
    from sqlalchemy.exc import OperationalError
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import get_settings

    engine = create_async_engine(get_settings().database_url)
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except (OSError, OperationalError):
        pytest.skip("PostgreSQL is not available")
    finally:
        await engine.dispose()

    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/accounts", json={})
        assert created.status_code == 201
        body = created.json()
        assert is_valid_mnemonic(body["mnemonic"]) is True
        await client.post(
            "/api/v1/accounts/logout",
            headers={"Authorization": f"Bearer {body['access_token']}"},
        )
        login = await client.post("/api/v1/accounts/login", json={"mnemonic": body["mnemonic"]})
        assert login.status_code == 200
        assert login.json()["public_id"] == body["public_id"]
        share = await client.patch(
            "/api/v1/accounts/me/share",
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
            json={"is_public": True},
        )
        assert share.status_code == 200
        assert share.json()["is_public"] is True
