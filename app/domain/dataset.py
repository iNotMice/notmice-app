"""Public dataset records. These objects carry no internal ids and no secrets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal


def published_chronological_age(value: Decimal | None) -> Decimal | None:
    """Whole years for the public dataset.

    A tenth of a year next to the collection date approximates a birth month.
    The public read and the CC0 export publish the age rounded to a whole year.
    """
    if value is None:
        return None
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class DatasetError(Exception):
    """Base error for public dataset reads."""


class ProfileNotPublicError(DatasetError):
    """The profile is missing or has not opted into the public dataset."""


@dataclass(frozen=True, slots=True)
class PublicBiomarkerRow:
    """One confirmed analyte visible because its owner opted in."""

    public_id: str
    collected_at: date | None
    chronological_age: Decimal | None
    loinc_code: str | None
    canonical_name: str | None
    raw_name: str
    value: Decimal
    unit: str
    mapping_status: str


@dataclass(frozen=True, slots=True)
class PublicDatasetPage:
    """A slice of the public biomarker table plus the unpaged total."""

    rows: tuple[PublicBiomarkerRow, ...]
    total: int
    limit: int
    offset: int


@dataclass(frozen=True, slots=True)
class PublicTimeseriesPoint:
    """Markers collected together on one date."""

    collected_at: date | None
    chronological_age: Decimal | None
    markers: tuple[PublicBiomarkerRow, ...]


@dataclass(frozen=True, slots=True)
class PublicTimeseries:
    """Confirmed history for a single opted-in public id."""

    public_id: str
    points: tuple[PublicTimeseriesPoint, ...]
