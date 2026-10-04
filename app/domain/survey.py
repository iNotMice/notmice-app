"""Controlled participant profile fields for the optional survey."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Final, Literal

import pycountry
from pydantic import BaseModel, ConfigDict, Field, field_validator

SexAtBirth = Literal["female", "male", "intersex", "undisclosed"]
Smoking = Literal["never", "former", "current"]
Alcohol = Literal["none", "light", "moderate", "heavy"]
Activity = Literal["sedentary", "light", "moderate", "high"]

COUNTRY_CODES: Final[tuple[str, ...]] = tuple(
    sorted(country.alpha_2 for country in pycountry.countries)
)
_COUNTRY_CODE_SET: Final[frozenset[str]] = frozenset(COUNTRY_CODES)
PROFILE_CONDITION_CODES: Final[frozenset[str]] = frozenset()
PROFILE_GOAL_CODES: Final[frozenset[str]] = frozenset()

SEX_AT_BIRTH: tuple[SexAtBirth, ...] = ("female", "male", "intersex", "undisclosed")
SMOKING: tuple[Smoking, ...] = ("never", "former", "current")
ALCOHOL: tuple[Alcohol, ...] = ("none", "light", "moderate", "heavy")
ACTIVITY: tuple[Activity, ...] = ("sedentary", "light", "moderate", "high")


class ParticipantProfileInput(BaseModel):
    """Survey answers use bounded values only; no free text or full date of birth."""

    model_config = ConfigDict(extra="forbid")

    sex_at_birth: SexAtBirth | None = None
    year_of_birth: int | None = Field(default=None, ge=1900, le=2015)
    country: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    height_cm: int | None = Field(default=None, ge=100, le=250)
    weight_kg: Decimal | None = Field(default=None, ge=30, le=400, max_digits=5, decimal_places=2)
    smoking: Smoking | None = None
    alcohol: Alcohol | None = None
    activity: Activity | None = None
    conditions: list[str] = Field(default_factory=list, max_length=40)

    @field_validator("conditions")
    @classmethod
    def condition_codes_are_known(cls, values: list[str]) -> list[str]:
        """Reject duplicates and conditions outside the draft controlled vocabulary."""
        if len(values) != len(set(values)):
            raise ValueError("duplicate condition code")
        if set(values) - PROFILE_CONDITION_CODES:
            raise ValueError("condition vocabulary is not approved or code is unknown")
        return values

    @field_validator("country")
    @classmethod
    def country_code_is_iso_3166(cls, value: str | None) -> str | None:
        """Accept only assigned ISO-3166-1 alpha-2 country codes."""
        if value is not None and value not in _COUNTRY_CODE_SET:
            raise ValueError("unknown ISO-3166-1 alpha-2 country code")
        return value


@dataclass(frozen=True, slots=True)
class ParticipantProfile:
    """Owner-only profile record, separate from the participant identity."""

    sex_at_birth: SexAtBirth | None
    year_of_birth: int | None
    country: str | None
    height_cm: int | None
    weight_kg: Decimal | None
    smoking: Smoking | None
    alcohol: Alcohol | None
    activity: Activity | None
    conditions: tuple[str, ...]
    updated_at: datetime | None


@dataclass(frozen=True, slots=True)
class SurveyCatalog:
    """Controlled values visible to the participant profile form."""

    enabled: bool
    health_data_consent_version: str
    research_reuse_consent_version: str
    profile_consent_version: str | None
    public_sharing_consent_version: str
    countries: tuple[str, ...]
    sex_at_birth: tuple[SexAtBirth, ...]
    smoking: tuple[Smoking, ...]
    alcohol: tuple[Alcohol, ...]
    activity: tuple[Activity, ...]
    conditions: tuple[str, ...]
    goals: tuple[str, ...]


def profile_from_input(payload: ParticipantProfileInput) -> ParticipantProfile:
    """Convert a validated write payload to its persistence-neutral value."""
    return ParticipantProfile(
        sex_at_birth=payload.sex_at_birth,
        year_of_birth=payload.year_of_birth,
        country=payload.country,
        height_cm=payload.height_cm,
        weight_kg=payload.weight_kg,
        smoking=payload.smoking,
        alcohol=payload.alcohol,
        activity=payload.activity,
        conditions=tuple(sorted(payload.conditions)),
        updated_at=None,
    )
