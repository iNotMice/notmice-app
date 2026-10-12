"""CC0 snapshots of the opt-in biomarker table. No HTTP and no ORM models."""

from __future__ import annotations

import csv
import io
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime
from decimal import Decimal

import pyarrow as pa
import pyarrow.parquet as pq
import structlog

from app.domain.dataset import PublicBiomarkerRow, published_chronological_age
from app.domain.export import (
    DATASET_LICENSE_ID,
    DATASET_LICENSE_NAME,
    DATASET_LICENSE_URL,
    EXPORT_COLUMNS,
)
from app.domain.pii import reject_sensitive_output
from app.services.dataset import DatasetStore

logger = structlog.get_logger(__name__)

_PARQUET_SCHEMA: pa.Schema = pa.schema(
    [
        pa.field("public_id", pa.string(), nullable=False),
        pa.field("collected_at", pa.date32(), nullable=True),
        pa.field("chronological_age", pa.float64(), nullable=True),
        pa.field("loinc_code", pa.string(), nullable=True),
        pa.field("canonical_name", pa.string(), nullable=True),
        pa.field("raw_name", pa.string(), nullable=False),
        pa.field("value", pa.float64(), nullable=False),
        pa.field("unit", pa.string(), nullable=False),
        pa.field("mapping_status", pa.string(), nullable=False),
    ]
).with_metadata(
    {
        b"license": DATASET_LICENSE_ID.encode(),
        b"license_name": DATASET_LICENSE_NAME.encode(),
        b"license_url": DATASET_LICENSE_URL.encode(),
    }
)


def _decimal_text(value: Decimal) -> str:
    """Render a decimal without binary float noise or trailing zeros."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _optional_decimal_text(value: Decimal | None) -> str:
    """Render an optional decimal, or an empty CSV cell."""
    if value is None:
        return ""
    return _decimal_text(value)


def _csv_record(row: PublicBiomarkerRow) -> dict[str, str]:
    """One CSV record. Keys are exactly the public column contract."""
    collected = "" if row.collected_at is None else row.collected_at.isoformat()
    return {
        "public_id": row.public_id,
        "collected_at": collected,
        "chronological_age": _optional_decimal_text(
            published_chronological_age(row.chronological_age)
        ),
        "loinc_code": row.loinc_code or "",
        "canonical_name": row.canonical_name or "",
        "raw_name": row.raw_name,
        "value": _decimal_text(row.value),
        "unit": row.unit,
        "mapping_status": row.mapping_status,
    }


def _parquet_record(row: PublicBiomarkerRow) -> dict[str, object]:
    """One Parquet record. Missing dates and ages stay null."""
    published_age = published_chronological_age(row.chronological_age)
    age = None if published_age is None else float(published_age)
    return {
        "public_id": row.public_id,
        "collected_at": row.collected_at,
        "chronological_age": age,
        "loinc_code": row.loinc_code,
        "canonical_name": row.canonical_name,
        "raw_name": row.raw_name,
        "value": float(row.value),
        "unit": row.unit,
        "mapping_status": row.mapping_status,
    }


def _guard(records: Sequence[Mapping[str, object]]) -> None:
    """Refuse to encode a snapshot whose keys left the public column contract."""
    reject_sensitive_output(list(records))
    for record in records:
        if tuple(record) != EXPORT_COLUMNS:
            raise ValueError("Export record columns drifted from the public contract")


def render_csv(rows: Sequence[PublicBiomarkerRow]) -> bytes:
    """Encode opted-in rows as UTF-8 CSV with a stable header.

    Args:
        rows: Confirmed analytes already limited to public profiles.
    """
    records = [_csv_record(row) for row in rows]
    _guard(records)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=EXPORT_COLUMNS,
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    writer.writerows(records)
    return buffer.getvalue().encode("utf-8")


def render_parquet(rows: Sequence[PublicBiomarkerRow]) -> bytes:
    """Encode opted-in rows as an Apache Parquet file stamped CC0-1.0.

    Args:
        rows: Confirmed analytes already limited to public profiles.
    """
    records = [_parquet_record(row) for row in rows]
    _guard(records)
    if records:
        table = pa.Table.from_pylist(records, schema=_PARQUET_SCHEMA)
    else:
        table = _PARQUET_SCHEMA.empty_table()
    sink = io.BytesIO()
    pq.write_table(table, sink)
    return sink.getvalue()


def _count_missing(rows: Sequence[PublicBiomarkerRow], field: str) -> int:
    """Count rows whose public field is absent."""
    missing = 0
    for row in rows:
        if getattr(row, field) is None:
            missing += 1
    return missing


def _date_span(rows: Sequence[PublicBiomarkerRow]) -> str:
    """Describe the earliest and latest collection dates in the snapshot."""
    dates = [row.collected_at for row in rows if row.collected_at is not None]
    if not dates:
        return "none"
    earliest: date = min(dates)
    latest: date = max(dates)
    return f"{earliest.isoformat()} to {latest.isoformat()}"


def render_datasheet(rows: Sequence[PublicBiomarkerRow], *, generated_at: datetime) -> str:
    """Write a Datasheets-for-Datasets markdown file for this snapshot.

    Args:
        rows: Confirmed analytes already limited to public profiles.
        generated_at: UTC timestamp printed in the file. The caller supplies it
            so a test can freeze the clock.
    """
    _guard([_csv_record(row) for row in rows])
    profiles = len({row.public_id for row in rows})
    profile_word = "profile" if profiles == 1 else "profiles"
    loinc_codes = {row.loinc_code for row in rows if row.loinc_code}
    statuses = Counter(row.mapping_status for row in rows)
    status_line = ", ".join(f"{name}: {statuses[name]}" for name in sorted(statuses)) or "none"
    stamp = generated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Datasheet: NotMice public biomarker dataset",
        "",
        f"Generated: {stamp}",
        "",
        "This file follows the section outline of Datasheets for Datasets (Gebru et al., 2021).",
        "It describes the snapshot in this response. The next request rebuilds it from Postgres.",
        "",
        "## Motivation",
        "",
        "NotMice publishes confirmed laboratory biomarker rows for profiles that opted in.",
        "The export exists so researchers can use those anonymized measurements.",
        "It is not a medical device and it is not a clinical record.",
        "",
        "## Composition",
        "",
        f"- Instances: {len(rows)} confirmed biomarker rows",
        f"- Profiles: {profiles} pseudonymous {profile_word}",
        f"- Collection dates: {_date_span(rows)}",
        f"- Distinct LOINC codes: {len(loinc_codes)}",
        f"- Missing collected_at: {_count_missing(rows, 'collected_at')}",
        f"- Missing chronological_age: {_count_missing(rows, 'chronological_age')}",
        f"- Missing loinc_code: {_count_missing(rows, 'loinc_code')}",
        f"- Missing canonical_name: {_count_missing(rows, 'canonical_name')}",
        f"- Mapping status: {status_line}",
        "",
        "Each instance is one analyte on one collection, not one person-visit pivoted wide.",
        "",
        "| Column | Description |",
        "| --- | --- |",
        "| public_id | Pseudonymous profile id. Not an internal database id. |",
        "| collected_at | Collection date (ISO 8601) when the lab report states it. |",
        "| chronological_age | Age in whole years at collection. "
        "The fractional year is not published. Date of birth is not in this export. |",
        "| loinc_code | LOINC code when the dictionary mapped the analyte. |",
        "| canonical_name | Dictionary name when the analyte is mapped. |",
        "| raw_name | Analyte name as confirmed from the report. |",
        "| value | Numeric result as confirmed. |",
        "| unit | Unit as confirmed. |",
        "| mapping_status | `mapped` or `unmapped`. |",
        "",
        "Names, dates of birth, patient numbers, lab account numbers, seed hashes,",
        "document hashes, and internal UUIDs are not columns in this export.",
        "",
        "## Collection process",
        "",
        "A participant confirms extracted lab values, which are stored in Postgres.",
        "A row is included only when that profile has public sharing on and the lab result",
        "is confirmed. Turning public sharing off removes the profile from the next snapshot.",
        "Original PDF and image files are not retained.",
        "",
        "## Preprocessing, cleaning, and labeling",
        "",
        "Analyte names are matched to a versioned LOINC dictionary.",
        "Unmatched analytes stay in the export with an empty LOINC code and status unmapped.",
        "Values are the confirmed numbers. This table does not add a PhenoAge score.",
        "",
        "## Uses",
        "",
        "Suitable for research on anonymized laboratory measurements.",
        "Not suitable for identifying a person, for diagnosis, or for treatment decisions.",
        "Phenotypic Age elsewhere in NotMice is a research index, not a medical service.",
        "",
        "## Distribution",
        "",
        f"License: {DATASET_LICENSE_NAME} ({DATASET_LICENSE_ID}).",
        DATASET_LICENSE_URL,
        "",
        "This snapshot is dedicated to the public domain under that instrument.",
        "The same rows are available as CSV and Apache Parquet from the read-only API.",
        "",
        "## Maintenance",
        "",
        "Each download is a live snapshot of opted-in confirmed rows in Postgres.",
        "This response is not a separately frozen release.",
        "A profile that opts out disappears from later snapshots.",
        "Copies already downloaded are not recalled.",
        "",
    ]
    return "\n".join(lines)


class ExportService:
    """Load the full opt-in table for a CC0 snapshot."""

    def __init__(self, store: DatasetStore) -> None:
        self._store = store

    async def load_rows(self) -> tuple[PublicBiomarkerRow, ...]:
        """Return every confirmed analyte on profiles that opted in.

        Opt-out profiles and unconfirmed results are absent because the store
        query already excludes them.
        """
        total = await self._store.count_public_biomarkers()
        if total == 0:
            logger.info("public_dataset_export_loaded", rows=0)
            return ()
        rows = await self._store.list_public_biomarkers(limit=total, offset=0)
        _guard([_csv_record(row) for row in rows])
        logger.info("public_dataset_export_loaded", rows=len(rows))
        return rows
