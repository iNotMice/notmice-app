"""Localized account mail, the 18+ sign-up rule, and laboratory password reset."""

# ruff: noqa: RUF001

from __future__ import annotations

from datetime import UTC, datetime
from typing import get_args

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError

from app.api.lab_accounts import LAB_SESSION_COOKIE_NAME
from app.core.deps import (
    get_account_identity_rate_limiter,
    get_account_rate_limiter,
    get_lab_account_service,
)
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.lab_accounts import LabAuthTokenError, LabInvalidCredentialsError
from app.domain.locales import MailLocale
from app.domain.survey import ParticipantProfileInput, latest_adult_birth_year
from app.main import create_app
from app.services.lab_accounts import LabAccountService
from app.services.mail_templates import MailKind, account_mail, mail_locale
from app.services.mailer import CapturingMailer
from app.tests.test_accounts import _override_app
from app.tests.test_email_accounts import _email_service, _register_body
from app.tests.test_lab_accounts import InMemoryLabAccountStore
from app.tests.test_lab_accounts import _service as _lab_service
from app.tests.test_lab_accounts import _token as _lab_token

_LINK = "https://notmice.example/?confirm=abc"
_LAB_PASSWORD = "correct-horse-battery"
_NEW_PASSWORD = "a-brand-new-lab-password"


@pytest.mark.parametrize("kind", get_args(MailKind))
@pytest.mark.parametrize("locale", get_args(MailLocale))
def test_every_mail_carries_the_link_once(kind: MailKind, locale: str) -> None:
    """Each kind and language has a subject, and the body holds the link on its own line."""
    subject, body = account_mail(kind, locale, _LINK)
    assert subject.strip()
    assert body.splitlines().count(_LINK) == 1
    assert "NotMice" in body


def test_unknown_language_falls_back_to_english() -> None:
    """A missing or unsupported language never breaks delivery."""
    assert mail_locale(None) == "en"
    assert mail_locale("es") == "en"
    assert account_mail("confirm", "xx", _LINK) == account_mail("confirm", "en", _LINK)


def test_russian_mail_is_russian() -> None:
    """A Russian reader gets a Russian subject and body."""
    subject, body = account_mail("reset", "ru", _LINK)
    assert subject == "Сброс пароля NotMice"
    assert "Ссылка одноразовая" in body


async def test_sign_up_requires_the_adult_confirmation() -> None:
    """Without adult_confirmed=true the request is refused and no mail is sent."""
    service, _users, mailer = _email_service()
    transport = ASGITransport(app=_override_app(service))
    body = _register_body("person@example.com")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        missing = await client.post(
            "/api/v1/accounts",
            json={key: value for key, value in body.items() if key != "adult_confirmed"},
        )
        declined = await client.post("/api/v1/accounts", json={**body, "adult_confirmed": False})
    assert missing.status_code == 422
    assert declined.status_code == 422
    assert mailer.sent == []


async def test_sign_up_mail_follows_the_reader_language() -> None:
    """The confirmation message is written in the language the form was filled in."""
    service, _users, mailer = _email_service()
    transport = ASGITransport(app=_override_app(service))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post(
            "/api/v1/accounts",
            json={**_register_body("person@example.com"), "locale": "ru"},
        )
    assert created.status_code == 202
    assert mailer.sent[-1].subject == "Подтвердите аккаунт NotMice"


def test_survey_refuses_a_birth_year_under_18() -> None:
    """The questionnaire accepts adults only; the bound moves with the calendar year."""
    latest = latest_adult_birth_year()
    assert ParticipantProfileInput(year_of_birth=latest).year_of_birth == latest
    with pytest.raises(ValidationError, match="18 years"):
        ParticipantProfileInput(year_of_birth=latest + 1)
    assert latest_adult_birth_year(datetime(2026, 10, 12, tzinfo=UTC)) == 2008


async def _confirmed_lab() -> tuple[LabAccountService, InMemoryLabAccountStore, CapturingMailer]:
    service, store, mailer = _lab_service()
    await service.register(
        name="Example Research Lab",
        org_type="laboratory",
        country="DE",
        email="owner@example-lab.org",
        password=_LAB_PASSWORD,
    )
    await service.confirm_email(_lab_token(mailer))
    return service, store, mailer


async def test_lab_password_reset_replaces_the_password_and_ends_sessions() -> None:
    """A confirmed lab user can reset the password; old sessions and the old password stop."""
    service, store, mailer = await _confirmed_lab()
    _user, cookie = await service.login("owner@example-lab.org", _LAB_PASSWORD)
    await service.request_password_reset("Owner@Example-Lab.org", "de")
    assert mailer.sent[-1].subject == "Passwort des NotMice-Laborkontos zurücksetzen"
    token = _lab_token(mailer, "reset=")
    assert "/lab?reset=" in mailer.sent[-1].body
    await service.reset_password(token, _NEW_PASSWORD)
    with pytest.raises(LabInvalidCredentialsError):
        await service.login("owner@example-lab.org", _LAB_PASSWORD)
    await service.login("owner@example-lab.org", _NEW_PASSWORD)
    with pytest.raises(LabAuthTokenError):
        await service.reset_password(token, _NEW_PASSWORD)
    assert all(digest != cookie for digest in store.sessions)


async def test_lab_reset_sends_nothing_for_unknown_or_unconfirmed_addresses() -> None:
    """The caller cannot learn whether an address exists or is confirmed."""
    service, _store, mailer = _lab_service()
    await service.register(
        name="Pending Lab",
        org_type="laboratory",
        country="DE",
        email="pending@example-lab.org",
        password=_LAB_PASSWORD,
    )
    sent_before = len(mailer.sent)
    await service.request_password_reset("pending@example-lab.org")
    await service.request_password_reset("nobody@example-lab.org")
    assert len(mailer.sent) == sent_before


def _lab_app(service: LabAccountService) -> FastAPI:
    application = create_app()

    async def override() -> LabAccountService:
        return service

    application.dependency_overrides[get_lab_account_service] = override
    application.dependency_overrides[get_account_rate_limiter] = lambda: SlidingWindowRateLimiter(
        limit=1000, window_seconds=60
    )
    application.dependency_overrides[get_account_identity_rate_limiter] = lambda: (
        SlidingWindowRateLimiter(limit=1000, window_seconds=60)
    )
    return application


async def test_lab_reset_routes_answer_the_same_and_clear_the_cookie() -> None:
    """Request answers 202 for any address; confirm sets the password and clears the cookie."""
    service, _store, mailer = await _confirmed_lab()
    transport = ASGITransport(app=_lab_app(service))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unknown = await client.post(
            "/api/v1/lab/password-reset", json={"email": "nobody@example-lab.org"}
        )
        invalid = await client.post("/api/v1/lab/password-reset", json={"email": "not-an-email"})
        known = await client.post(
            "/api/v1/lab/password-reset",
            json={"email": "owner@example-lab.org", "locale": "ru"},
        )
        token = _lab_token(mailer, "reset=")
        bad = await client.post(
            "/api/v1/lab/password-reset/confirm",
            json={"token": "x" * 40, "password": _NEW_PASSWORD},
        )
        done = await client.post(
            "/api/v1/lab/password-reset/confirm",
            json={"token": token, "password": _NEW_PASSWORD},
        )
    assert unknown.status_code == known.status_code == invalid.status_code == 202
    assert unknown.json() == known.json()
    assert mailer.sent[-1].subject == "Сброс пароля лаборатории NotMice"
    assert bad.status_code == 400
    assert done.status_code == 204
    assert LAB_SESSION_COOKIE_NAME in done.headers.get("set-cookie", "")
