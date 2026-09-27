"""Upload/extract domain records and errors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import MappingStatus
from app.domain.loinc import LoincDictionary, normalize_analyte_name

PARSER_NAME = "notmice-extract"
PARSER_RELEASE = "1.0"


class UploadError(Exception):
    """Base error for extract and confirm use-cases."""


class UnsupportedMediaTypeError(UploadError):
    """The file is not a PDF or a supported image."""


class PayloadTooLargeError(UploadError):
    """The in-memory file exceeded the configured size limit."""


class EmptyPayloadError(UploadError):
    """The upload contained no bytes."""


class VisionNotConfiguredError(UploadError):
    """The selected Vision provider has no API key or is not implemented."""


class VisionTimeoutError(UploadError):
    """The Vision provider did not answer before the configured deadline."""


class VisionExtractionError(UploadError):
    """The Vision provider failed after retries."""

    def __init__(self, message: str, *, tokens_used: int | None = 0) -> None:
        super().__init__(message)
        self.tokens_used = tokens_used


class ExtractSessionNotFoundError(UploadError):
    """The extract token is missing, expired, or belongs to another user."""


class NoMarkersError(UploadError):
    """Extraction produced no numeric analytes."""


class GeminiBudgetExhaustedError(UploadError):
    """The daily Gemini token or call budget cannot cover this extract."""

    def __init__(self, *, tokens_used: int, tokens_limit: int) -> None:
        super().__init__("Daily extraction limit reached")
        self.tokens_used = tokens_used
        self.tokens_limit = tokens_limit


class RawMarker(BaseModel):
    """One analyte as returned by pdfplumber/Vision before persistence."""

    model_config = ConfigDict(extra="forbid")

    raw_name: str = Field(min_length=1, max_length=255)
    value: float
    unit: str = Field(min_length=1, max_length=32)
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)


class RawLabExtraction(BaseModel):
    """Structured lab panel used as the Gemini/Claude response schema."""

    model_config = ConfigDict(extra="forbid")

    lab_name: str | None = Field(default=None, max_length=255)
    collected_at: str | None = Field(default=None, description="ISO date YYYY-MM-DD if present.")
    chronological_age: float | None = Field(default=None, ge=0, le=120)
    markers: list[RawMarker] = Field(default_factory=list)


@dataclass(frozen=True, slots=True)
class MappedMarker:
    """A raw analyte after local LOINC/canonical matching."""

    raw_name: str
    value: Decimal
    unit: str
    confidence: float
    canonical_id: str | None
    loinc_code: str | None
    mapping_status: MappingStatus
    within_range: bool | None


@dataclass(frozen=True, slots=True)
class ExtractedPanel:
    """RAM-only extract result. Never includes the original file bytes."""

    document_sha256: str
    parser_version: str
    lab_name: str | None
    collected_at: date | None
    chronological_age: Decimal | None
    markers: tuple[MappedMarker, ...]


@dataclass(frozen=True, slots=True)
class ExtractSession:
    """Temporary extract token payload. File bytes are not stored."""

    token: str
    user_id: UUID
    panel: ExtractedPanel
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CompletedExtract:
    """Extract session plus the caller's personal Gemini counter."""

    session: ExtractSession
    tokens_used: int
    tokens_limit: int
    warning: bool


@dataclass(frozen=True, slots=True)
class ConfirmedLabResult:
    """Persisted panel after human sign-off."""

    lab_result_id: UUID
    document_sha256: str
    parser_version: str
    confirmed_at: datetime
    marker_count: int


@dataclass(frozen=True, slots=True)
class OwnedMarker:
    """One analyte returned to the account that confirmed it."""

    raw_name: str
    canonical_id: str | None
    loinc_code: str | None
    value: Decimal
    unit: str


@dataclass(frozen=True, slots=True)
class OwnedLabPanel:
    """A confirmed panel for its owner. No internal user id."""

    collected_at: date | None
    lab_name: str | None
    chronological_age: Decimal | None
    confirmed_at: datetime
    document_sha256: str
    markers: tuple[OwnedMarker, ...]


def usable_chronological_age(value: Decimal | float | None) -> Decimal | None:
    """Return ``value`` when it is an age in years, otherwise ``None``.

    A birth year copied from a lab header is not an age and must not fail confirm.

    Args:
        value: Reported age, or ``None`` when the report did not state one.
    """
    if value is None:
        return None
    age = Decimal(str(value))
    if age < 1 or age > 120:
        return None
    return age


def parser_version_for(provider: str, model: str, *, dictionary_version: str) -> str:
    """Return a provenance parser version string.

    Args:
        provider: ``gemini`` or ``claude``.
        model: Provider model id.
        dictionary_version: LOINC dictionary release used for this extract.
    """
    return f"{PARSER_NAME}/{PARSER_RELEASE}/{provider}/{model}+loinc-{dictionary_version}"


def map_marker(raw: RawMarker, dictionary: LoincDictionary) -> MappedMarker:
    """Attach a LOINC code when the dictionary knows the analyte name.

    Unrecognised names stay ``unmapped`` and are not dropped. Known units are
    scaled to the canonical unit. A value outside the plausible window stays
    mapped and is flagged so a typo is visible at review.

    Args:
        raw: Marker as extracted by pdfplumber or Vision.
        dictionary: Versioned LOINC catalog.
    """
    entry = dictionary.find(normalize_analyte_name(raw.raw_name))
    value = Decimal(str(raw.value))
    if entry is None:
        return MappedMarker(
            raw_name=raw.raw_name.strip(),
            value=value,
            unit=raw.unit.strip(),
            confidence=raw.confidence,
            canonical_id=None,
            loinc_code=None,
            mapping_status=MappingStatus.UNMAPPED,
            within_range=None,
        )
    converted = entry.convert(value, raw.unit)
    within_range = entry.within_range(converted.value) if converted.unit_recognized else None
    return MappedMarker(
        raw_name=raw.raw_name.strip(),
        value=converted.value,
        unit=converted.unit,
        confidence=raw.confidence,
        canonical_id=entry.entry_id,
        loinc_code=entry.loinc,
        mapping_status=MappingStatus.MAPPED,
        within_range=within_range,
    )


def parse_collected_at(value: str | None) -> date | None:
    """Parse an ISO date from model output, or return None if unusable.

    Args:
        value: YYYY-MM-DD or empty.
    """
    if value is None:
        return None
    text = value.strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None
