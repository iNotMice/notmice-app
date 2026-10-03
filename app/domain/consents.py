"""Consent catalogue for account registration. No I/O."""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.accounts import ConsentRequiredError, ConsentVersionError

HEALTH_DATA = "health_data"
HEALTH_DATA_VERSION = "2026-09-28"
RESEARCH_REUSE = "research_reuse"
RESEARCH_REUSE_VERSION = "2026-09-28"
PARTICIPANT_PROFILE = "participant_profile"
# Legal approval is pending. Keep this unset so the profile-specific consent
# cannot be granted until its purpose and wording have been approved.
PARTICIPANT_PROFILE_VERSION: str | None = None

REQUIRED_CONSENTS: dict[str, str] = {HEALTH_DATA: HEALTH_DATA_VERSION}
OPTIONAL_CONSENTS: dict[str, str] = {RESEARCH_REUSE: RESEARCH_REUSE_VERSION}
if PARTICIPANT_PROFILE_VERSION is not None:
    OPTIONAL_CONSENTS[PARTICIPANT_PROFILE] = PARTICIPANT_PROFILE_VERSION


@dataclass(frozen=True, slots=True)
class ConsentChoice:
    """One checkbox from the registration or consent form."""

    consent_type: str
    text_version: str
    accepted: bool


def grants_to_store(choices: tuple[ConsentChoice, ...]) -> tuple[tuple[str, str], ...]:
    """Return the consent rows that should be inserted.

    Required consents must be accepted at the current text version.
    Optional consents are stored only when accepted. A missing optional
    checkbox stays off.

    Args:
        choices: Submitted checkboxes.

    Raises:
        ConsentRequiredError: A required consent is missing, declined, or duplicated.
        ConsentVersionError: A known consent uses an old text version.
    """
    by_type = {choice.consent_type: choice for choice in choices}
    if len(by_type) != len(choices):
        raise ConsentRequiredError
    granted: list[tuple[str, str]] = []
    for consent_type, version in REQUIRED_CONSENTS.items():
        choice = by_type.get(consent_type)
        if choice is None or not choice.accepted:
            raise ConsentRequiredError
        if choice.text_version != version:
            raise ConsentVersionError
        granted.append((consent_type, version))
    for consent_type, version in OPTIONAL_CONSENTS.items():
        choice = by_type.get(consent_type)
        if choice is None or not choice.accepted:
            continue
        if choice.text_version != version:
            raise ConsentVersionError
        granted.append((consent_type, version))
    known = set(REQUIRED_CONSENTS) | set(OPTIONAL_CONSENTS)
    if any(choice.consent_type not in known for choice in choices):
        raise ConsentVersionError
    return tuple(granted)


def current_version(consent_type: str) -> str | None:
    """Return the current text version for a known consent type, or None."""
    if consent_type in REQUIRED_CONSENTS:
        return REQUIRED_CONSENTS[consent_type]
    return OPTIONAL_CONSENTS.get(consent_type)
