"""Participant profile validation, consent gates, ownership, and deletion."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import ValidationError
from sqlalchemy.orm import configure_mappers

from app.api.accounts import get_current_user
from app.core.config import Settings, validate_survey_config
from app.core.deps import get_account_service, get_survey_service
from app.core.security import Argon2SeedHasher
from app.domain.accounts import AccountExport, ConsentRecord, UserRecord
from app.domain.consents import (
    HEALTH_DATA,
    HEALTH_DATA_VERSION,
    PARTICIPANT_PROFILE,
    PARTICIPANT_PROFILE_VERSION,
    ConsentChoice,
)
from app.domain.survey import ParticipantProfile, ParticipantProfileInput, profile_from_input
from app.main import create_app
from app.repositories.models import Base
from app.repositories.survey import SurveyRepository
from app.services.accounts import AccountService, UserStore
from app.services.survey import SurveyService


class InMemorySurveyRepository(SurveyRepository):
    """Owner-scoped profile storage for API tests."""

    def __init__(self) -> None:
        self.profiles: dict[UUID, ParticipantProfile] = {}

    async def get_profile(self, user_id: UUID) -> ParticipantProfile | None:
        return self.profiles.get(user_id)

    async def save_profile(
        self, user_id: UUID, profile: ParticipantProfile
    ) -> ParticipantProfile | None:
        self.profiles[user_id] = profile
        return profile

    async def delete_profile(self, user_id: UUID) -> bool:
        return self.profiles.pop(user_id, None) is not None


class InMemoryAccountService:
    """Minimal consent lookup used by the survey endpoint tests."""

    def __init__(self, consents: tuple[ConsentRecord, ...] = ()) -> None:
        self.consents = consents

    async def list_consents(self, user_id: UUID) -> tuple[ConsentRecord, ...]:
        del user_id
        return self.consents

    async def set_consent(self, user_id: UUID, choice: ConsentChoice) -> ConsentRecord | None:
        del user_id
        consent_type = choice.consent_type
        text_version = choice.text_version
        accepted = choice.accepted
        now = datetime.now(UTC)
        previous = next(
            (
                row
                for row in reversed(self.consents)
                if row.consent_type == consent_type
                and row.text_version == text_version
                and row.withdrawn_at is None
            ),
            None,
        )
        if accepted:
            row = ConsentRecord(
                consent_type=consent_type,
                text_version=text_version,
                granted_at=now,
                withdrawn_at=None,
            )
        elif previous is not None:
            row = ConsentRecord(
                consent_type=consent_type,
                text_version=text_version,
                granted_at=previous.granted_at,
                withdrawn_at=now,
            )
        else:
            return None
        self.consents = (*self.consents, row)
        return row


class InMemoryExportStore:
    """An account export fixture containing the owner's optional profile."""

    def __init__(self, user_id: UUID, bundle: AccountExport) -> None:
        self.user_id = user_id
        self.bundle = bundle

    async def export_account(self, user_id: UUID) -> AccountExport | None:
        return self.bundle if user_id == self.user_id else None


def _user() -> UserRecord:
    return UserRecord(
        id=uuid4(),
        public_id="participant-test",
        is_public=False,
        created_at=datetime(2026, 10, 3, tzinfo=UTC),
    )


def _consent(consent_type: str, version: str) -> ConsentRecord:
    return ConsentRecord(
        consent_type=consent_type,
        text_version=version,
        granted_at=datetime(2026, 10, 3, tzinfo=UTC),
        withdrawn_at=None,
    )


def _application(
    user: UserRecord,
    repository: InMemorySurveyRepository,
    accounts: InMemoryAccountService,
    *,
    enabled: bool,
) -> FastAPI:
    application = create_app()
    survey = SurveyService(repository, enabled=enabled)

    async def override_user() -> UserRecord:
        return user

    async def override_accounts() -> AccountService:
        return cast(AccountService, accounts)

    async def override_survey() -> SurveyService:
        return survey

    application.dependency_overrides[get_current_user] = override_user
    application.dependency_overrides[get_account_service] = override_accounts
    application.dependency_overrides[get_survey_service] = override_survey
    return application


def test_profile_input_rejects_unknown_values_and_free_text() -> None:
    """The profile accepts only bounded values and approved controlled codes."""
    with pytest.raises(ValidationError):
        ParticipantProfileInput.model_validate({"name": "Ada"})
    with pytest.raises(ValidationError):
        ParticipantProfileInput.model_validate({"smoking": "sometimes"})
    with pytest.raises(ValidationError):
        ParticipantProfileInput.model_validate({"conditions": ["unknown_condition"]})
    with pytest.raises(ValidationError):
        ParticipantProfileInput.model_validate({"conditions": ["anemia"]})
    with pytest.raises(ValidationError):
        ParticipantProfileInput.model_validate({"country": "ZZ"})


def test_profile_orm_relationships_and_tables_are_registered() -> None:
    """Profile relationships load in SQLAlchemy metadata for migrations and queries."""
    configure_mappers()
    assert "participant_profiles" in Base.metadata.tables
    assert "profile_conditions" in Base.metadata.tables


def test_profile_input_preserves_bounded_profile_values() -> None:
    """Bounded country and numeric values pass validation without free text."""
    profile = profile_from_input(
        ParticipantProfileInput(
            sex_at_birth="female",
            country="DE",
            weight_kg=Decimal("67.50"),
        )
    )
    assert profile.conditions == ()
    assert profile.country == "DE"
    assert profile.weight_kg == Decimal("67.50")


def test_startup_allows_survey_only_with_approved_consent_version() -> None:
    """The approved source-controlled profile consent permits explicit opt-in rollout."""
    validate_survey_config(Settings(survey_enabled=True))


@pytest.mark.asyncio
async def test_owner_export_includes_profile_in_json_and_csv() -> None:
    """The participant's portability exports include profile answers."""
    user = _user()
    profile = replace(
        profile_from_input(
            ParticipantProfileInput(
                country="DE",
                year_of_birth=1980,
                weight_kg=Decimal("67.50"),
            )
        ),
        updated_at=datetime(2026, 10, 3, tzinfo=UTC),
    )
    bundle = AccountExport(
        public_id=user.public_id,
        email=None,
        is_public=False,
        created_at=user.created_at,
        consents=(),
        markers=(),
        profile=profile,
    )
    store = InMemoryExportStore(user.id, bundle)
    service = AccountService(
        users=cast(UserStore, store),
        hasher=Argon2SeedHasher("test-pepper-secret-key-32-bytes!!"),
    )

    json_export = json.loads(await service.export_json(user.id))
    csv_export = await service.export_csv(user.id)
    csv_rows = list(csv.DictReader(csv_export.splitlines()))
    assert json_export["profile"]["country"] == "DE"
    assert json_export["profile"]["conditions"] == []
    assert len(csv_rows) == 1
    assert csv_rows[0]["record_type"] == "profile"
    assert csv_rows[0]["profile_weight_kg"] == "67.5"


@pytest.mark.asyncio
async def test_catalog_and_profile_collection_are_closed_by_default() -> None:
    """The catalog is visible but profile writes stay unavailable before approval."""
    user = _user()
    repository = InMemorySurveyRepository()
    app = _application(
        user,
        repository,
        InMemoryAccountService(),
        enabled=False,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        catalog = await client.get("/api/v1/survey/catalog")
        response = await client.put(
            "/api/v1/accounts/me/profile",
            json={"country": "DE"},
        )
    assert catalog.status_code == 200
    assert catalog.json()["enabled"] is False
    assert "DE" in catalog.json()["countries"]
    assert catalog.json()["profile_consent_version"] == "2026-10-03"
    assert catalog.json()["public_sharing_consent_version"] == "2026-10-03"
    assert catalog.json()["goals"] == []
    assert response.status_code == 503
    assert repository.profiles == {}


@pytest.mark.asyncio
async def test_profile_requires_both_active_consents(monkeypatch: pytest.MonkeyPatch) -> None:
    """Even an enabled profile endpoint refuses requests without both grants."""
    monkeypatch.setattr(
        "app.services.survey.PARTICIPANT_PROFILE_VERSION",
        "test-profile-consent-v1",
    )
    user = _user()
    repository = InMemorySurveyRepository()
    app = _application(
        user,
        repository,
        InMemoryAccountService((_consent(HEALTH_DATA, HEALTH_DATA_VERSION),)),
        enabled=True,
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/api/v1/accounts/me/profile",
            json={"country": "DE"},
        )
    assert response.status_code == 403
    assert repository.profiles == {}


@pytest.mark.asyncio
async def test_consented_profile_is_owner_scoped_and_deletable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An authenticated user can only read, replace, and delete their own answers."""
    profile_version = "test-profile-consent-v1"
    monkeypatch.setattr("app.services.survey.PARTICIPANT_PROFILE_VERSION", profile_version)
    user = _user()
    other_user_id = uuid4()
    repository = InMemorySurveyRepository()
    foreign_profile = profile_from_input(ParticipantProfileInput(country="FR"))
    repository.profiles[other_user_id] = foreign_profile
    repository.profiles[user.id] = profile_from_input(ParticipantProfileInput(country="DE"))
    accounts = InMemoryAccountService(
        (
            _consent(HEALTH_DATA, HEALTH_DATA_VERSION),
            _consent(PARTICIPANT_PROFILE, profile_version),
        )
    )
    app = _application(user, repository, accounts, enabled=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        read_response = await client.get("/api/v1/accounts/me/profile")
        write_response = await client.put(
            "/api/v1/accounts/me/profile",
            json={"country": "NL"},
        )
        delete_response = await client.delete("/api/v1/accounts/me/profile")
    assert read_response.status_code == 200
    assert read_response.json()["country"] == "DE"
    assert write_response.status_code == 200
    assert write_response.json()["country"] == "NL"
    assert delete_response.status_code == 204
    assert user.id not in repository.profiles
    assert repository.profiles[other_user_id] == foreign_profile


@pytest.mark.asyncio
async def test_withdrawing_profile_consent_deletes_saved_profile() -> None:
    user = _user()
    repository = InMemorySurveyRepository()
    repository.profiles[user.id] = profile_from_input(ParticipantProfileInput(country="DE"))
    accounts = InMemoryAccountService(
        (
            _consent(HEALTH_DATA, HEALTH_DATA_VERSION),
            _consent(PARTICIPANT_PROFILE, PARTICIPANT_PROFILE_VERSION),
        )
    )
    application = _application(user, repository, accounts, enabled=True)
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/accounts/me/consents",
            json={
                "type": PARTICIPANT_PROFILE,
                "version": PARTICIPANT_PROFILE_VERSION,
                "accepted": False,
            },
        )

    assert response.status_code == 200
    assert user.id not in repository.profiles
    assert any(
        row.consent_type == HEALTH_DATA and row.withdrawn_at is None for row in accounts.consents
    )
