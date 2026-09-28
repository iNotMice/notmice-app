"""Protocol journal: own rows, personal export, and a closed public snapshot."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.accounts import get_current_user
from app.core.deps import get_account_service, get_protocol_service
from app.domain.accounts import ExportedProtocolEntry, UserRecord
from app.domain.export import EXPORT_COLUMNS
from app.domain.protocol import (
    ProtocolDraft,
    ProtocolEntry,
    ProtocolValidationError,
    protocol_draft,
)
from app.domain.schemas import ProtocolEntryInput
from app.main import create_app
from app.repositories.dataset import public_biomarker_select
from app.services.export import ExportService, render_csv, render_datasheet, render_parquet
from app.services.protocol import ProtocolService
from app.tests.test_accounts import InMemoryUserStore, _service
from app.tests.test_dataset import _store

_STARTED = date(2026, 1, 2)
_SECRET_TITLE = "Zinc-bisglycinate-d1"
_SECRET_DOSE = "25 mg zinc-d1"
_SECRET_NOTE = "with breakfast d1"


class InMemoryProtocolStore:
    """Process-local journal. A foreign id is indistinguishable from a missing one."""

    def __init__(self) -> None:
        self.rows: dict[UUID, list[ProtocolEntry]] = {}

    async def list_for_user(self, user_id: UUID) -> tuple[ProtocolEntry, ...]:
        return tuple(self.rows.get(user_id, []))

    async def insert(self, user_id: UUID, draft: ProtocolDraft, *, now: datetime) -> ProtocolEntry:
        del now
        entry = ProtocolEntry(
            id=uuid4(),
            kind=draft.kind,
            title=draft.title,
            dose=draft.dose,
            started_on=draft.started_on,
            ended_on=draft.ended_on,
            note=draft.note,
        )
        self.rows.setdefault(user_id, []).append(entry)
        return entry

    async def replace(
        self,
        user_id: UUID,
        entry_id: UUID,
        draft: ProtocolDraft,
        *,
        now: datetime,
    ) -> ProtocolEntry | None:
        del now
        owned = self.rows.get(user_id, [])
        for index, entry in enumerate(owned):
            if entry.id == entry_id:
                updated = ProtocolEntry(
                    id=entry.id,
                    kind=draft.kind,
                    title=draft.title,
                    dose=draft.dose,
                    started_on=draft.started_on,
                    ended_on=draft.ended_on,
                    note=draft.note,
                )
                owned[index] = updated
                return updated
        return None

    async def delete(self, user_id: UUID, entry_id: UUID) -> bool:
        owned = self.rows.get(user_id, [])
        kept = [entry for entry in owned if entry.id != entry_id]
        if len(kept) == len(owned):
            return False
        self.rows[user_id] = kept
        return True


def _user() -> UserRecord:
    return UserRecord(
        id=uuid4(),
        public_id="public-journal",
        is_public=False,
        created_at=datetime(2026, 9, 28, tzinfo=UTC),
    )


def _body(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "kind": "supplement",
        "title": "Magnesium glycinate",
        "dose": "200 mg",
        "started_on": "2026-01-02",
        "ended_on": None,
        "note": "evening",
    }
    payload.update(overrides)
    return payload


def _application(store: InMemoryProtocolStore, user: UserRecord) -> FastAPI:
    application = create_app()
    service = ProtocolService(store)

    async def override_service() -> ProtocolService:
        return service

    async def override_user() -> UserRecord:
        return user

    application.dependency_overrides[get_protocol_service] = override_service
    application.dependency_overrides[get_current_user] = override_user
    return application


def test_open_period_and_two_word_supplement_name_are_stored() -> None:
    """An empty end date is a still-open period. A supplement name is not a person."""
    draft = protocol_draft(
        kind="supplement",
        title="  Magnesium Glycinate  ",
        dose="  ",
        started_on=_STARTED,
        ended_on=None,
        note=None,
    )
    assert draft.title == "Magnesium Glycinate"
    assert draft.dose is None
    assert draft.ended_on is None


def test_end_before_start_and_a_personal_note_are_rejected() -> None:
    """The period has to run forward, and a note cannot carry a person's name."""
    with pytest.raises(ProtocolValidationError, match="End date"):
        protocol_draft(
            kind="sleep",
            title="Lights out",
            dose=None,
            started_on=_STARTED,
            ended_on=date(2026, 1, 1),
            note=None,
        )
    with pytest.raises(ProtocolValidationError, match="Forbidden field"):
        protocol_draft(
            kind="other",
            title="Walk",
            dose=None,
            started_on=_STARTED,
            ended_on=None,
            note="Asked Maria Ivanova",
        )


def test_catalog_id_is_not_a_journal_field() -> None:
    """A reference id is rejected. This version has no dictionary."""
    with pytest.raises(ValueError):
        ProtocolEntryInput.model_validate(_body(reference_id="A11CC30"))


async def test_owner_can_list_replace_and_delete_only_their_rows() -> None:
    """Another account's id answers as not found, and the row stays put."""
    store = InMemoryProtocolStore()
    owner = _user()
    stranger = _user()
    owner_app = _application(store, owner)
    stranger_app = _application(store, stranger)
    transport = ASGITransport(app=owner_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/protocol", json=_body())
        assert created.status_code == 201
        entry_id = created.json()["id"]
        assert created.json()["ended_on"] is None
        listed = await client.get("/api/v1/protocol")
        assert listed.status_code == 200
        assert listed.json()["entries"][0]["title"] == "Magnesium glycinate"
        replaced = await client.patch(
            f"/api/v1/protocol/{entry_id}",
            json=_body(title="Magnesium citrate", dose=None, ended_on="2026-02-01"),
        )
        assert replaced.status_code == 200
        assert replaced.json()["title"] == "Magnesium citrate"
        assert replaced.json()["dose"] is None
    stranger_transport = ASGITransport(app=stranger_app)
    async with AsyncClient(transport=stranger_transport, base_url="http://test") as client:
        missing = await client.patch(
            f"/api/v1/protocol/{entry_id}",
            json=_body(),
        )
        assert missing.status_code == 404
        assert missing.json()["detail"] == "Entry not found"
        gone = await client.delete(f"/api/v1/protocol/{entry_id}")
        assert gone.status_code == 404
        hidden = await client.get("/api/v1/protocol")
        assert hidden.json()["entries"] == []
    assert store.rows[owner.id][0].title == "Magnesium citrate"


async def test_journal_requires_a_session() -> None:
    """A missing cookie is not a journal."""
    application = create_app()
    users = InMemoryUserStore()
    service, _users = _service(users)

    async def override_accounts() -> object:
        return service

    async def override_protocol() -> ProtocolService:
        return ProtocolService(InMemoryProtocolStore())

    application.dependency_overrides[get_account_service] = override_accounts
    application.dependency_overrides[get_protocol_service] = override_protocol
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/protocol")
    assert response.status_code == 401


async def test_personal_export_includes_the_journal() -> None:
    """The owner's JSON and CSV carry the title, dose, and note."""
    users = InMemoryUserStore()
    service, users = _service(users)
    created = await service.create()
    users.exported_protocol[created.user.id] = (
        ExportedProtocolEntry(
            kind="supplement",
            title=_SECRET_TITLE,
            dose=_SECRET_DOSE,
            started_on=_STARTED,
            ended_on=None,
            note=_SECRET_NOTE,
        ),
    )
    body = json.loads(await service.export_json(created.user.id))
    assert body["protocol"][0]["title"] == _SECRET_TITLE
    assert body["protocol"][0]["dose"] == _SECRET_DOSE
    assert body["protocol"][0]["note"] == _SECRET_NOTE
    csv_body = await service.export_csv(created.user.id)
    assert _SECRET_TITLE in csv_body
    assert _SECRET_DOSE in csv_body
    assert _SECRET_NOTE in csv_body


async def test_public_snapshot_does_not_contain_a_journal_entry() -> None:
    """Creating a row does not add its text to the CC0 files or the public query."""
    store = InMemoryProtocolStore()
    user = _user()
    await ProtocolService(store).create_entry(
        user.id,
        kind="supplement",
        title=_SECRET_TITLE,
        dose=_SECRET_DOSE,
        started_on=_STARTED,
        ended_on=None,
        note=_SECRET_NOTE,
    )
    assert store.rows[user.id][0].title == _SECRET_TITLE
    rows = await ExportService(_store()).load_rows()
    csv_body = render_csv(rows)
    parquet_body = render_parquet(rows)
    datasheet = render_datasheet(rows, generated_at=datetime(2026, 9, 28, tzinfo=UTC))
    blob = csv_body + parquet_body + datasheet.encode()
    assert _SECRET_TITLE.encode() not in blob
    assert _SECRET_DOSE.encode() not in blob
    assert _SECRET_NOTE.encode() not in blob
    assert "entry_title" not in EXPORT_COLUMNS
    assert "protocol_entries" not in str(public_biomarker_select().compile())


async def test_journal_text_stays_out_of_postgres_research_packages() -> None:
    """A real row is in the personal export and absent from the public dataset files."""
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
        await engine.dispose()
        pytest.skip("PostgreSQL is not available")
    await engine.dispose()

    title = f"Zinc-{uuid4().hex}"
    dose = f"dose-{uuid4().hex}"
    note = f"note-{uuid4().hex}"
    email = f"journal-{uuid4().hex}@example.com"
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
        body = next(row["body"] for row in logs if row.get("event") == "auth_mail_dev")
        token = str(body).split("confirm=", maxsplit=1)[1].split()[0]
        confirmed = await client.post("/api/v1/accounts/confirm", json={"token": token})
        assert confirmed.status_code == 200
        public_id = confirmed.json()["public_id"]
        saved = await client.post(
            "/api/v1/protocol",
            json={
                "kind": "supplement",
                "title": title,
                "dose": dose,
                "started_on": "2026-03-01",
                "ended_on": None,
                "note": note,
            },
        )
        assert saved.status_code == 201
        shared = await client.patch("/api/v1/accounts/me/share", json={"is_public": True})
        assert shared.status_code == 200
        personal = await client.get("/api/v1/accounts/me/export.json")
        assert personal.status_code == 200
        assert title in personal.text
        assert dose in personal.text
        assert note in personal.text
        personal_csv = await client.get("/api/v1/accounts/me/export.csv")
        assert title in personal_csv.text
        dataset = await client.get("/api/v1/dataset")
        csv_export = await client.get("/api/v1/dataset.csv")
        parquet_export = await client.get("/api/v1/dataset.parquet")
        datasheet = await client.get("/api/v1/dataset/datasheet")
        series = await client.get(f"/api/v1/profiles/{public_id}/timeseries")
        public_blob = (
            dataset.text + csv_export.text + parquet_export.text + datasheet.text + series.text
        )
        assert title not in public_blob
        assert dose not in public_blob
        assert note not in public_blob
        deleted = await client.delete("/api/v1/accounts/me")
        assert deleted.status_code == 204

    check = create_async_engine(get_settings().database_url)
    try:
        async with check.connect() as connection:
            remaining = await connection.execute(
                text("SELECT count(*) FROM protocol_entries WHERE title = :title"),
                {"title": title},
            )
            assert remaining.scalar_one() == 0
    finally:
        await check.dispose()
