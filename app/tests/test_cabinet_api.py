"""Cabinet HTTP: owner-only overview, password change, signing out other devices."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.accounts import SESSION_COOKIE_NAME
from app.core.deps import get_cabinet_service
from app.domain.accounts import UnauthenticatedError
from app.domain.enums import MappingStatus
from app.domain.uploads import MappedMarker
from app.services.accounts import AccountService
from app.services.cabinet import CabinetService
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.image_redact import PassthroughImageRedactor
from app.services.protocol import ProtocolService
from app.services.uploads import UploadService
from app.tests.test_accounts import _override_app
from app.tests.test_email_accounts import _PASSWORD, _email_service, _register_body, _token_from
from app.tests.test_protocol import InMemoryProtocolStore
from app.tests.test_uploads import FakeVision, InMemoryLabStore, _budget


def _mapped(canonical_id: str, value: str) -> MappedMarker:
    return MappedMarker(
        raw_name=canonical_id,
        value=Decimal(value),
        unit="u",
        confidence=0.99,
        canonical_id=canonical_id,
        loinc_code=None,
        mapping_status=MappingStatus.MAPPED,
        within_range=None,
        reported_value=Decimal(value),
        reported_unit="u",
    )


async def _save(labs: InMemoryLabStore, user_id: UUID, collected_at: date) -> None:
    await labs.save_confirmed(
        user_id=user_id,
        collected_at=collected_at,
        lab_name="Lab A",
        chronological_age=Decimal("45"),
        parser_version="test",
        confirmed_at=datetime(2026, 10, 1, tzinfo=UTC),
        document_sha256="b" * 64,
        markers=(_mapped("albumin", "44"), _mapped("crp", "1.5")),
    )


def _cabinet_app(service: AccountService, labs: InMemoryLabStore) -> FastAPI:
    application = _override_app(service)
    uploads = UploadService(
        vision=FakeVision(),
        sessions=InMemoryExtractSessionStore(ttl_seconds=60),
        lab_results=labs,
        max_upload_bytes=1_000_000,
        budget=_budget(),
        image_redactor=PassthroughImageRedactor(),
    )
    cabinet = CabinetService(
        accounts=service,
        uploads=uploads,
        protocol=ProtocolService(InMemoryProtocolStore()),
    )

    async def override() -> CabinetService:
        return cabinet

    application.dependency_overrides[get_cabinet_service] = override
    return application


async def _signed_in(client: AsyncClient, mailer_token: str) -> str:
    confirmed = await client.post("/api/v1/accounts/confirm", json={"token": mailer_token})
    assert confirmed.status_code == 200
    cookie = confirmed.cookies.get(SESSION_COOKIE_NAME)
    assert cookie is not None
    return cookie


async def test_cabinet_requires_a_session() -> None:
    service, _users, _mailer = _email_service()
    application = _cabinet_app(service, InMemoryLabStore())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/accounts/me/cabinet")
    assert response.status_code == 401


async def test_cabinet_shows_only_the_owner_and_no_secrets() -> None:
    service, _users, mailer = _email_service()
    labs = InMemoryLabStore()
    application = _cabinet_app(service, labs)
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        await _signed_in(client, _token_from(mailer))
        owner = await service.login_email("person@example.com", _PASSWORD)
        await _save(labs, owner.user.id, date(2026, 3, 1))
        await _save(labs, owner.user.id, date(2026, 7, 1))
        other = await service.create()
        await _save(labs, other.user.id, date(2026, 9, 1))

        response = await client.get("/api/v1/accounts/me/cabinet")

    assert response.status_code == 200
    body = response.json()
    assert body["account"]["email"] == "person@example.com"
    assert body["account"]["sign_in_method"] == "email"
    assert body["account"]["active_sessions"] == 2
    assert body["history"]["panel_count"] == 2
    assert body["history"]["first_observed_on"] == "2026-03-01"
    assert body["history"]["last_observed_on"] == "2026-07-01"
    assert body["history"]["repeat_marker_count"] == 2
    assert body["latest_index"] is None
    assert body["consents"]["health_data"] is True
    assert body["consents"]["sharing_enabled"] is False
    assert "creatinine" in body["history"]["latest_missing_markers"]
    for secret in ("password_hash", "document_sha256", "token_sha256", "seed_phrase"):
        assert secret not in response.text


async def test_password_change_checks_the_current_one_and_signs_out_other_devices() -> None:
    service, _users, mailer = _email_service()
    application = _cabinet_app(service, InMemoryLabStore())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        await _signed_in(client, _token_from(mailer))
        elsewhere = await service.login_email("person@example.com", _PASSWORD)

        wrong = await client.post(
            "/api/v1/accounts/me/password",
            json={"current_password": "not-the-password", "new_password": "a-brand-new-password"},
        )
        assert wrong.status_code == 400

        short = await client.post(
            "/api/v1/accounts/me/password",
            json={"current_password": _PASSWORD, "new_password": "short"},
        )
        assert short.status_code == 422

        changed = await client.post(
            "/api/v1/accounts/me/password",
            json={"current_password": _PASSWORD, "new_password": "a-brand-new-password"},
        )
        assert changed.status_code == 200
        assert changed.json() == {"revoked_sessions": 1}

        still_here = await client.get("/api/v1/accounts/me")
        assert still_here.status_code == 200

    with pytest.raises(UnauthenticatedError):
        await service.authenticate(elsewhere.session_token)
    relogin = await service.login_email("person@example.com", "a-brand-new-password")
    assert relogin.user.public_id == elsewhere.user.public_id


async def test_sign_out_other_devices_keeps_the_current_one() -> None:
    service, _users, mailer = _email_service()
    application = _cabinet_app(service, InMemoryLabStore())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        await client.post("/api/v1/accounts", json=_register_body("person@example.com"))
        await _signed_in(client, _token_from(mailer))
        await service.login_email("person@example.com", _PASSWORD)
        await service.login_email("person@example.com", _PASSWORD)

        revoked = await client.post("/api/v1/accounts/me/sessions/revoke-others")
        assert revoked.status_code == 200
        assert revoked.json() == {"revoked_sessions": 2}

        overview = await client.get("/api/v1/accounts/me/cabinet")
        assert overview.json()["account"]["active_sessions"] == 1


async def test_phrase_account_has_no_password_to_change() -> None:
    service, _users, _mailer = _email_service()
    created = await service.create()
    application = _cabinet_app(service, InMemoryLabStore())
    async with AsyncClient(
        transport=ASGITransport(app=application), base_url="http://test"
    ) as client:
        client.cookies.set(SESSION_COOKIE_NAME, created.session_token)
        response = await client.post(
            "/api/v1/accounts/me/password",
            json={"current_password": "anything", "new_password": "a-brand-new-password"},
        )
        overview = await client.get("/api/v1/accounts/me/cabinet")
    assert response.status_code == 409
    assert overview.json()["account"]["sign_in_method"] == "phrase"
    assert overview.json()["account"]["email"] is None
