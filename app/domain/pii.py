"""PII rejection helpers. Name, date of birth, and patient numbers must never enter the API."""

import re
from collections.abc import Mapping, Sequence
from typing import Final

FORBIDDEN_PII_KEYS: Final[frozenset[str]] = frozenset(
    {
        "full_name",
        "first_name",
        "last_name",
        "given_name",
        "family_name",
        "fio",
        "date_of_birth",
        "dob",
        "birth_date",
        "birthday",
        "patient_number",
        "patient_id",
        "medical_record_number",
        "mrn",
        "lab_account_number",
    }
)

# Internal identifiers and secrets that must never appear on the public read API.
SENSITIVE_OUTPUT_KEYS: Final[frozenset[str]] = FORBIDDEN_PII_KEYS | frozenset(
    {
        "user_id",
        "lab_result_id",
        "biomarker_id",
        "provenance_id",
        "entered_by_user_id",
        "seed_phrase_hash",
        "document_sha256",
        "mnemonic",
        "access_token",
        "internal_id",
    }
)


# Free-text fields where a 2-3 word capitalized name is personal, not a key name.
_FREE_TEXT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "raw_name",
        "lab_name",
        "notes",
        "note",
        "comment",
        "comments",
    }
)

# Words that keep a lab or analyte label from being read as a person's name.
# "Quest Diagnostics" and "Serum Albumin" stay valid because of these tokens.
_LAB_LABEL_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "serum",
        "albumin",
        "creatinine",
        "fasting",
        "glucose",
        "lymphocyte",
        "percentage",
        "mean",
        "corpuscular",
        "volume",
        "red",
        "cell",
        "distribution",
        "width",
        "alkaline",
        "phosphatase",
        "white",
        "blood",
        "count",
        "hemoglobin",
        "haemoglobin",
        "hematocrit",
        "haematocrit",
        "platelet",
        "platelets",
        "alanine",
        "aminotransferase",
        "aspartate",
        "total",
        "cholesterol",
        "triglyceride",
        "triglycerides",
        "thyrotropin",
        "ferritin",
        "protein",
        "reactive",
        "vitamin",
        "diagnostics",
        "diagnostic",
        "laboratory",
        "laboratories",
        "lab",
        "labs",
        "clinic",
        "hospital",
        "medical",
        "center",
        "centre",
        "health",
        "альбумин",
        "сыворотки",
        "сывороточный",
        "глюкоза",
        "креатинин",
        "гемоглобин",
        "фосфатаза",
        "щелочная",
        "общий",
        "холестерин",
        "лимфоциты",
        "лейкоциты",
        "тромбоциты",
        "ферритин",
        "триглицериды",
    }
)

_EMAIL_RE: Final[re.Pattern[str]] = re.compile(
    r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}"
)
# Formatted numbers only. A bare digit run or hyphenated id must not count as a phone,
# or extract tokens and hashes would be rejected.
# Free-text fields also use _LOOSE_PHONE_RE, which allows 415-555-2671.
_PHONE_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![\w@])(?:"
    r"\+\d{1,3}[\s.\-]?\(?\d{2,4}\)?(?:[\s.\-]?\d{2,4}){2,4}"
    r"|\(\d{3}\)[\s.\-]?\d{3}[\s.\-]?\d{4}"
    r"|8[\s\-]\(?\d{3}\)?[\s\-]\d{3}[\s\-]\d{2}[\s\-]\d{2}"
    r")(?!\d)"
)
_LOOSE_PHONE_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)\+?\d[\d\s().\-]{8,20}\d(?!\d)")
_PERSON_NAME_RE: Final[re.Pattern[str]] = re.compile(
    r"\b[A-Z\u0410-\u042f\u0401][a-z\u0430-\u044f\u0451]+"
    r"(?:[ ]+[A-Z\u0410-\u042f\u0401][a-z\u0430-\u044f\u0451]+){1,2}\b"
)


class PIIValidationError(ValueError):
    """Raised when a payload contains a forbidden personally identifying key or value."""


def reject_pii(payload: object, *, _path: str = "$") -> None:
    """Walk a JSON-like object and reject forbidden PII keys and obvious PII values.

    Email addresses and phone numbers are rejected in every string. A personal name
    (two or three capitalized Cyrillic or Latin words) is rejected only in free-text
    fields such as ``raw_name``, ``lab_name``, and notes. Lab labels that contain a
    clinical token, including ``Quest Diagnostics`` and ``Serum Albumin``, are kept.

    Args:
        payload: Mapping, sequence, or scalar to inspect.
        _path: JSON-path used in error messages.

    Raises:
        PIIValidationError: If a forbidden key or value is present at any depth.
    """
    _reject_keys(payload, FORBIDDEN_PII_KEYS, label="Forbidden PII key", _path=_path)
    _reject_content(payload, parent_key=None, _path=_path)


def reject_sensitive_output(payload: object, *, _path: str = "$") -> None:
    """Reject PII keys, internal identifiers, and obvious PII values on a public response.

    Email, phone, and free-text personal names use the same rules as ``reject_pii``.

    Args:
        payload: Mapping, sequence, or scalar about to be returned.
        _path: JSON-path used in error messages.

    Raises:
        PIIValidationError: If a forbidden key or value is present at any depth.
    """
    _reject_keys(payload, SENSITIVE_OUTPUT_KEYS, label="Forbidden sensitive key", _path=_path)
    _reject_content(payload, parent_key=None, _path=_path)


def _reject_keys(
    payload: object,
    forbidden: frozenset[str],
    *,
    label: str,
    _path: str,
) -> None:
    """Walk ``payload`` and raise when a key is in ``forbidden``."""
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            child_path = f"{_path}.{key_text}"
            if key_text.lower() in forbidden:
                raise PIIValidationError(f"{label} at {child_path}")
            _reject_keys(value, forbidden, label=label, _path=child_path)
        return
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for index, item in enumerate(payload):
            _reject_keys(item, forbidden, label=label, _path=f"{_path}[{index}]")


def _reject_content(payload: object, *, parent_key: str | None, _path: str) -> None:
    """Reject email, phone, and free-text personal names inside ``payload``."""
    if isinstance(payload, str):
        if _EMAIL_RE.search(payload):
            raise PIIValidationError(f"Forbidden email at {_path}")
        if _contains_phone(payload) or _contains_loose_phone(payload, parent_key):
            raise PIIValidationError(f"Forbidden phone at {_path}")
        if (
            parent_key is not None
            and parent_key.lower() in _FREE_TEXT_KEYS
            and _contains_person_name(payload)
        ):
            raise PIIValidationError(f"Forbidden person name at {_path}")
        return
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            key_text = str(key)
            _reject_content(value, parent_key=key_text, _path=f"{_path}.{key_text}")
        return
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for index, item in enumerate(payload):
            _reject_content(item, parent_key=parent_key, _path=f"{_path}[{index}]")


def contains_personal_text(value: str, *, parent_key: str) -> bool:
    """Return True when ``value`` would be rejected as personal data in ``parent_key``.

    Args:
        value: Free-text field about to be stored.
        parent_key: JSON key the checker uses, such as ``lab_name`` or ``raw_name``.
    """
    try:
        reject_pii({parent_key: value})
    except PIIValidationError:
        return True
    return False


def _contains_phone(value: str) -> bool:
    """Return True when ``value`` contains a 10-15 digit phone-shaped number."""
    return _match_has_phone_digits(_PHONE_RE, value)


def _contains_loose_phone(value: str, parent_key: str | None) -> bool:
    """Return True when a free-text field contains a separator-style phone number."""
    if parent_key is None or parent_key.lower() not in _FREE_TEXT_KEYS:
        return False
    return _match_has_phone_digits(_LOOSE_PHONE_RE, value)


def _match_has_phone_digits(pattern: re.Pattern[str], value: str) -> bool:
    """Return True when a match contains 10-15 digits."""
    for match in pattern.finditer(value):
        digits = "".join(character for character in match.group() if character.isdigit())
        if 10 <= len(digits) <= 15:
            return True
    return False


def _contains_person_name(value: str) -> bool:
    """Return True when ``value`` contains a 2-3 word name that is not a lab label."""
    for match in _PERSON_NAME_RE.finditer(value):
        words = match.group(0).split(" ")
        if all(word.casefold() not in _LAB_LABEL_TOKENS for word in words):
            return True
    return False
