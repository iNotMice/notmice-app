"""CC0 exports are built from the public store: opt-out rows stay out."""

from __future__ import annotations

import csv
import io
from datetime import UTC, date, datetime
from decimal import Decimal

import pyarrow.parquet as pq
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.deps import get_export_service, get_public_rate_limiter
from app.core.rate_limit import SlidingWindowRateLimiter
from app.domain.dataset import PublicBiomarkerRow
from app.domain.export import DATASET_LICENSE_ID, EXPORT_COLUMNS
from app.domain.pii import SENSITIVE_OUTPUT_KEYS
from app.main import create_app
from app.services.export import ExportService, render_csv, render_datasheet, render_parquet
from app.tests.test_dataset import (
    _PRIVATE,
    _PRIVATE_GLUCOSE,
    _PUBLIC,
    InMemoryDatasetStore,
    _store,
)

_GENERATED_AT = datetime(2026, 9, 22, 3, 37, tzinfo=UTC)


def _application(store: InMemoryDatasetStore, limiter: SlidingWindowRateLimiter) -> FastAPI:
    application = create_app()
    service = ExportService(store)

    async def override_service() -> ExportService:
        return service

    def override_limiter() -> SlidingWindowRateLimiter:
        return limiter

    application.dependency_overrides[get_export_service] = override_service
    application.dependency_overrides[get_public_rate_limiter] = override_limiter
    return application


def _csv_rows(payload: bytes) -> list[dict[str, str]]:
    reader = csv.DictReader(io.StringIO(payload.decode("utf-8")))
    assert reader.fieldnames is not None
    assert tuple(reader.fieldnames) == EXPORT_COLUMNS
    return list(reader)


async def test_export_snapshot_omits_private_and_unconfirmed_rows() -> None:
    """DoD: the file is the opt-in table, not a private or unconfirmed row."""
    rows = await ExportService(_store()).load_rows()
    assert {row.public_id for row in rows} == {_PUBLIC}
    assert _PRIVATE_GLUCOSE not in {row.value for row in rows}
    assert len(rows) == 2


async def test_csv_and_parquet_share_the_public_columns_and_cc0_license() -> None:
    """Both files carry the same opted-in values and no sensitive column names."""
    rows = await ExportService(_store()).load_rows()
    csv_body = render_csv(rows)
    parsed = _csv_rows(csv_body)
    assert {row["public_id"] for row in parsed} == {_PUBLIC}
    assert {row["value"] for row in parsed} == {"46.2", "90"}
    assert str(_PRIVATE_GLUCOSE) not in csv_body.decode()
    assert _PRIVATE not in csv_body.decode()
    assert set(parsed[0]).isdisjoint(SENSITIVE_OUTPUT_KEYS)

    table = pq.read_table(io.BytesIO(render_parquet(rows)))
    assert tuple(table.column_names) == EXPORT_COLUMNS
    assert table.schema.metadata[b"license"] == DATASET_LICENSE_ID.encode()
    assert set(table.column("public_id").to_pylist()) == {_PUBLIC}
    assert _PRIVATE_GLUCOSE not in {str(value) for value in table.column("value").to_pylist()}
    assert set(table.column_names).isdisjoint(SENSITIVE_OUTPUT_KEYS)


def test_public_export_publishes_age_in_whole_years() -> None:
    """A tenth of a year is not published next to the collection date."""
    low = PublicBiomarkerRow(
        public_id=_PUBLIC,
        collected_at=date(2024, 3, 2),
        chronological_age=Decimal("42.4"),
        loinc_code="1751-7",
        canonical_name="Albumin",
        raw_name="Serum Albumin",
        value=Decimal("46.2"),
        unit="g/L",
        mapping_status="mapped",
    )
    high = PublicBiomarkerRow(
        public_id=_PUBLIC,
        collected_at=date(2024, 6, 2),
        chronological_age=Decimal("42.6"),
        loinc_code="1751-7",
        canonical_name="Albumin",
        raw_name="Serum Albumin",
        value=Decimal("46.2"),
        unit="g/L",
        mapping_status="mapped",
    )
    parsed = _csv_rows(render_csv((low, high)))
    assert [row["chronological_age"] for row in parsed] == ["42", "43"]
    table = pq.read_table(io.BytesIO(render_parquet((low, high))))
    assert table.column("chronological_age").to_pylist() == [42.0, 43.0]
    text = render_datasheet((low,), generated_at=_GENERATED_AT)
    assert "whole years" in text


async def test_datasheet_describes_the_snapshot_under_cc0() -> None:
    """The datasheet counts public rows and states the CC0 dedication."""
    rows = await ExportService(_store()).load_rows()
    text = render_datasheet(rows, generated_at=_GENERATED_AT)
    assert "CC0-1.0" in text
    assert "Creative Commons Zero 1.0 Universal" in text
    assert "Instances: 2 confirmed biomarker rows" in text
    assert "Profiles: 1 pseudonymous profile" in text
    assert "Generated: 2026-09-22T03:37:00Z" in text
    assert "ipfs" not in text.lower()
    assert _PRIVATE not in text
    assert str(_PRIVATE_GLUCOSE) not in text
    assert "user_id" not in text
    assert "document_sha256" not in text


def test_empty_snapshot_still_exports_a_header_and_datasheet() -> None:
    """A dataset with nobody opted in is an empty file, not an error."""
    csv_body = render_csv(())
    parsed = _csv_rows(csv_body)
    assert parsed == []
    table = pq.read_table(io.BytesIO(render_parquet(())))
    assert table.num_rows == 0
    assert table.schema.metadata[b"license"] == DATASET_LICENSE_ID.encode()
    text = render_datasheet((), generated_at=_GENERATED_AT)
    assert "Instances: 0 confirmed biomarker rows" in text
    assert "CC0-1.0" in text


async def test_export_routes_are_read_only_cc0_downloads() -> None:
    """HTTP downloads match the store and advertise CC0. Writes are refused."""
    application = _application(_store(), SlidingWindowRateLimiter(limit=20, window_seconds=60))
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        csv_response = await client.get("/api/v1/dataset.csv")
        parquet_response = await client.get("/api/v1/dataset.parquet")
        datasheet_response = await client.get("/api/v1/dataset/datasheet")
        posted = await client.post("/api/v1/dataset.csv")
    assert csv_response.status_code == 200
    assert parquet_response.status_code == 200
    assert datasheet_response.status_code == 200
    assert posted.status_code == 405
    for response, filename in (
        (csv_response, "notmice-public-biomarkers.csv"),
        (parquet_response, "notmice-public-biomarkers.parquet"),
        (datasheet_response, "notmice-dataset-datasheet.md"),
    ):
        assert response.headers["x-dataset-license"] == DATASET_LICENSE_ID
        assert filename in response.headers["content-disposition"]
    parsed = _csv_rows(csv_response.content)
    assert {row["value"] for row in parsed} == {"46.2", "90"}
    assert str(_PRIVATE_GLUCOSE) not in csv_response.text
    assert b"PAR1" in parquet_response.content
    assert "Instances: 2 confirmed biomarker rows" in datasheet_response.text
    assert str(_PRIVATE_GLUCOSE) not in datasheet_response.text


async def test_export_rate_limit_is_per_ip() -> None:
    """Export downloads share the public per-IP limit."""
    application = _application(_store(), SlidingWindowRateLimiter(limit=2, window_seconds=60))
    transport = ASGITransport(app=application)
    headers = {"X-Real-IP": "203.0.113.20"}
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        first = await client.get("/api/v1/dataset.csv", headers=headers)
        second = await client.get("/api/v1/dataset.parquet", headers=headers)
        third = await client.get("/api/v1/dataset/datasheet", headers=headers)
        other = await client.get("/api/v1/dataset.csv", headers={"X-Real-IP": "203.0.113.21"})
    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert other.status_code == 200
