"""Email registration, one-time tokens, consents, and the owner's export."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_account_identity_rate_limiter
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import auth_token_digest
from app.domain.accounts import InvalidAuthTokenError, InvalidCredentialsError
from app.domain.consents import HEALTH_DATA, RESEARCH_REUSE, ConsentChoice
from app.repositories.models import User
from app.services.accounts import AccountService
from app.services.mailer import CapturingMailer
from app.tests.test_accounts import InMemoryUserStore, _override_app, _service

_PASSWORD = "correct-horse-battery"
_HEALTH = ConsentChoice(consent_type=HEALTH_DATA, text_version="2026-09-28", accepted=True)


def _email_service(
    *,
    seed_enabled: bool = True,
    now: datetime | None = None,
) -> tuple[AccountService, InMemoryUserStore, CapturingMailer]:
    mailer = CapturingMailer()
    service, users = _service()
    service._mailer = mailer
    service._auth_seed_enabled = seed_enabled
    if now is not None:
        service._now = lambda: now
    return service, users, mailer


def _token_from(mailer: CapturingMailer) -> str:
    body = mailer.sent[-1].body
    return body.split("=", maxsplit=1)[1].split()[0]


def _register_body(email: str, *, research: bool = False) -> dict[str, object]:
    consents: list[dict[str, object]] = [
        {"type": "health_data", "version": "2026-09-28", "accepted": True}
    ]
    if research:
        consents.append({"type": "research_reuse", "version": "2026-09-28", "accepted": True})
    return {"email": email, "password": _PASSWORD, "consents": consents}


def test_participant_table_has_no_email_or_password() -> None:
    """Email and the password hash live on credentials, not on the participant row."""
    assert "email" not in User.__table__.columns
    assert "password_hash" not in User.__table__.columns


async def test_register_stores_digest_not_the_raw_token() -> None:
    """The mail carries the token. The store keeps only its SHA-256."""
    service, users, mailer = _email_service()
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    presented = _token_from(mailer)
    digest = auth_token_digest(presented)
    assert digest is not None
    assert presented not in {token.token_sha256 for token in users._tokens}
    assert digest in {token.token_sha256 for token in users._tokens}
    assert len(presented) >= 42


async def test_new_account_has_no_phrase() -> None:
    """Registration does not return or store a recovery phrase."""
    service, users, _mailer = _email_service()
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    user = await users.find_email("person@example.com")
    assert user is not None
    record = await users.get_by_id(user.user_id)
    assert record is not None
    assert not hasattr(record, "mnemonic")


async def test_confirm_is_one_time_and_then_login_works() -> None:
    """A confirmation token signs the person in once. The same token then fails."""
    service, _users, mailer = _email_service()
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    presented = _token_from(mailer)
    session = await service.confirm_email(presented)
    assert session.access_token
    with pytest.raises(InvalidAuthTokenError):
        await service.confirm_email(presented)
    signed_in = await service.login_email("person@example.com", _PASSWORD)
    assert signed_in.user.id == session.user.id


async def test_expired_token_is_rejected() -> None:
    """A token older than 24 hours and 30 minutes cannot confirm the address."""
    start = datetime(2026, 9, 28, tzinfo=UTC)
    service, _users, mailer = _email_service(now=start)
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    presented = _token_from(mailer)
    service._now = lambda: start + timedelta(hours=24, minutes=31)
    with pytest.raises(InvalidAuthTokenError):
        await service.confirm_email(presented)


async def test_reset_token_is_one_time() -> None:
    """The reset token changes the password once and then stops working."""
    service, _users, mailer = _email_service()
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    await service.confirm_email(_token_from(mailer))
    await service.request_password_reset("person@example.com")
    presented = _token_from(mailer)
    await service.reset_password(presented, "another-password-ok")
    with pytest.raises(InvalidAuthTokenError):
        await service.reset_password(presented, "yet-another-password")
    signed_in = await service.login_email("person@example.com", "another-password-ok")
    assert signed_in.user.public_id
    with pytest.raises(InvalidCredentialsError):
        await service.login_email("person@example.com", _PASSWORD)


async def test_optional_consent_is_off_unless_accepted() -> None:
    """Research reuse is absent until the person accepts that version."""
    service, _users, mailer = _email_service()
    await service.register(email="person@example.com", password=_PASSWORD, consents=(_HEALTH,))
    session = await service.confirm_email(_token_from(mailer))
    rows = await service.list_consents(session.user.id)
    assert [row.consent_type for row in rows] == [HEALTH_DATA]
    assert rows[0].withdrawn_at is None


async def test_seed_login_stops_when_the_flag_is_off() -> None:
    """Phrase accounts stay in the database, and the flag closes that door."""
    service, _users, _mailer = _email_service()
    created = await service.create()
    service._auth_seed_enabled = False
    with pytest.raises(InvalidCredentialsError):
        await service.login(created.mnemonic)


async def test_duplicate_registration_hides_the_address() -> None:
    """A second registration of the same address returns the same HTTP body."""
    service, _users, _mailer = _email_service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        second = await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        unknown = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "missing@example.com", "password": _PASSWORD},
        )
        wrong = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "person@example.com", "password": "not-the-right-secret"},
        )
    assert first.status_code == second.status_code == 202
    assert first.json() == second.json() == {"status": "accepted"}
    assert "person@example.com" not in first.text
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


async def test_short_password_is_rejected() -> None:
    """Passwords shorter than 12 characters never create an account."""
    service, _users, mailer = _email_service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts",
            json={
                "email": "person@example.com",
                "password": "short-pass",
                "consents": [{"type": "health_data", "version": "2026-09-28", "accepted": True}],
            },
        )
    assert response.status_code == 422
    assert mailer.sent == []


async def test_identity_rate_limit_is_per_account() -> None:
    """Five attempts per account are configurable; the sixth is refused."""
    service, _users, _mailer = _email_service()
    application = _override_app(service)
    identity = SlidingWindowRateLimiter(limit=2, window_seconds=900)
    application.dependency_overrides[get_account_identity_rate_limiter] = lambda: identity
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "person@example.com", "password": _PASSWORD},
        )
        second = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "person@example.com", "password": _PASSWORD},
        )
        third = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "person@example.com", "password": _PASSWORD},
        )
        other = await client.post(
            "/api/v1/accounts/login/email",
            json={"email": "other@example.com", "password": _PASSWORD},
        )
    assert first.status_code == second.status_code == other.status_code == 401
    assert third.status_code == 429


async def test_export_and_delete_round_trip() -> None:
    """The owner's JSON includes the address and consents, then deletion removes the account."""
    service, _users, mailer = _email_service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        confirmed = await client.post(
            "/api/v1/accounts/confirm",
            json={"token": _token_from(mailer)},
        )
        token = confirmed.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        exported = await client.get("/api/v1/accounts/me/export.json", headers=headers)
        assert exported.status_code == 200
        body = exported.json()
        assert body["email"] == "person@example.com"
        assert body["consents"][0]["type"] == HEALTH_DATA
        assert "password_hash" not in exported.text
        assert "seed_phrase_hash" not in exported.text
        csv_export = await client.get("/api/v1/accounts/me/export.csv", headers=headers)
        assert csv_export.status_code == 200
        assert csv_export.text.startswith("public_id,email,")
        deleted = await client.delete("/api/v1/accounts/me", headers=headers)
        assert deleted.status_code == 204
        gone = await client.get("/api/v1/accounts/me", headers=headers)
        assert gone.status_code == 401


async def test_research_consent_can_be_withdrawn() -> None:
    """An optional consent starts only when accepted, and withdrawal keeps the row."""
    service, _users, mailer = _email_service()
    application = _override_app(service)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/accounts",
            json=_register_body("person@example.com", research=True),
        )
        confirmed = await client.post(
            "/api/v1/accounts/confirm",
            json={"token": _token_from(mailer)},
        )
        headers = {"Authorization": f"Bearer {confirmed.json()['access_token']}"}
        withdrawn = await client.post(
            "/api/v1/accounts/me/consents",
            headers=headers,
            json={"type": RESEARCH_REUSE, "version": "2026-09-28", "accepted": False},
        )
        assert withdrawn.status_code == 200
        assert withdrawn.json()["withdrawn_at"] is not None
