"""Protocol journal records. Free text only — no catalog id and no effect claim."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, cast
from uuid import UUID

from app.domain.enums import ProtocolKind
from app.domain.pii import PIIValidationError, reject_pii

ProtocolKindName = Literal["drug", "supplement", "nutrition", "activity", "sleep", "other"]

_TITLE_MAX = 120
_DOSE_MAX = 80
_NOTE_MAX = 2000


class ProtocolError(Exception):
    """Base error for journal writes."""


class ProtocolEntryNotFoundError(ProtocolError):
    """The id is missing, or it belongs to another participant."""


class ProtocolValidationError(ProtocolError):
    """The draft is not a journal row we can store."""


@dataclass(frozen=True, slots=True)
class ProtocolDraft:
    """Fields of one journal row after trimming and checks."""

    kind: ProtocolKindName
    title: str
    dose: str | None
    started_on: date
    ended_on: date | None
    note: str | None


@dataclass(frozen=True, slots=True)
class ProtocolEntry:
    """One stored journal row. The participant id stays in the repository."""

    id: UUID
    kind: ProtocolKindName
    title: str
    dose: str | None
    started_on: date
    ended_on: date | None
    note: str | None


def protocol_draft(
    *,
    kind: str,
    title: str,
    dose: str | None,
    started_on: date,
    ended_on: date | None,
    note: str | None,
) -> ProtocolDraft:
    """Trim a journal row and reject dates, contact data, and an unknown type.

    Args:
        kind: One of the six journal types.
        title: Free-text name. A two-word supplement name is allowed.
        dose: Optional dose text.
        started_on: First day of the period.
        ended_on: Last day, or None when the period is still open.
        note: Optional note. A personal name in this field is rejected.

    Raises:
        ProtocolValidationError: The row cannot be stored.
    """
    cleaned_title = title.strip()
    cleaned_dose = _blank_to_none(dose)
    cleaned_note = _blank_to_none(note)
    if kind not in ProtocolKind:
        raise ProtocolValidationError("Unknown journal type")
    if not cleaned_title:
        raise ProtocolValidationError("Title is required")
    if len(cleaned_title) > _TITLE_MAX:
        raise ProtocolValidationError("Title is too long")
    if cleaned_dose is not None and len(cleaned_dose) > _DOSE_MAX:
        raise ProtocolValidationError("Dose is too long")
    if cleaned_note is not None and len(cleaned_note) > _NOTE_MAX:
        raise ProtocolValidationError("Note is too long")
    if ended_on is not None and ended_on < started_on:
        raise ProtocolValidationError("End date is before the start date")
    payload = {"title": cleaned_title, "dose": cleaned_dose, "note": cleaned_note}
    try:
        reject_pii(payload)
    except PIIValidationError as exc:
        raise ProtocolValidationError("Forbidden field") from exc
    return ProtocolDraft(
        kind=cast(ProtocolKindName, kind),
        title=cleaned_title,
        dose=cleaned_dose,
        started_on=started_on,
        ended_on=ended_on,
        note=cleaned_note,
    )


def _blank_to_none(value: str | None) -> str | None:
    """Return stripped text, or None when the field was left empty."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped
