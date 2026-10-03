"""Cohort count suppression and the lab query contract.

Nothing in the API calls this module. The threshold 10 and the step 5 are the
starting values of ``publish_count``. They are not a portal setting: a lab
portal does not exist, and those numbers stay unapproved until the DPIA.

``CohortQuery`` is only the filter shape. It checks closed vocabularies and
rejects every field outside that shape, including the journal.
"""

from functools import lru_cache
from typing import Annotated, Final, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.domain.conditions import CONDITION_CODES
from app.services.loinc_dictionary import load_loinc_dictionary

# Starting values exercised by the tests. Not portal configuration.
_PUBLISH_MINIMUM: Final = 10
_PUBLISH_STEP: Final = 5
_MARKER_LIMIT: Final = 5
_COUNTRY_LIMIT: Final = 20
_CONDITION_LIMIT: Final = 10

SexAtBirth = Literal["female", "male", "intersex", "undisclosed"]
AgeBand = Literal["18-29", "30-39", "40-49", "50-59", "60-69", "70-plus"]
_CountryCode = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z]{2}$")]


@lru_cache(maxsize=1)
def _dictionary_loinc_codes() -> frozenset[str]:
    """Return LOINC codes from the packaged dictionary.

    Returns:
        The codes in ``dictionary.v1.json`` after dictionary validation.
    """
    return frozenset(entry.loinc for entry in load_loinc_dictionary().entries)


class CohortQuery(BaseModel):
    """A closed filter for a future lab cohort. It does not run a search.

    ``markers`` holds at most five LOINC codes from the packaged dictionary.
    ``sex_at_birth`` and ``age_bands`` use closed vocabularies, and the
    youngest age band is 18-29. ``countries`` holds at most twenty
    ISO-3166-1 alpha-2 codes. ``conditions`` holds at most ten codes from
    the draft condition dictionary. Any other field is rejected.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    markers: tuple[str, ...] = Field(default=(), max_length=_MARKER_LIMIT)
    sex_at_birth: tuple[SexAtBirth, ...] = ()
    age_bands: tuple[AgeBand, ...] = ()
    countries: tuple[_CountryCode, ...] = Field(default=(), max_length=_COUNTRY_LIMIT)
    conditions: tuple[str, ...] = Field(default=(), max_length=_CONDITION_LIMIT)

    @field_validator("markers")
    @classmethod
    def markers_are_known_loinc(cls, markers: tuple[str, ...]) -> tuple[str, ...]:
        """Reject a code that is not in the packaged LOINC dictionary."""
        known = _dictionary_loinc_codes()
        for code in markers:
            if code not in known:
                raise ValueError("unknown LOINC code")
        return markers

    @field_validator("conditions")
    @classmethod
    def conditions_are_draft_codes(cls, conditions: tuple[str, ...]) -> tuple[str, ...]:
        """Reject a condition code outside the draft dictionary."""
        for code in conditions:
            if code not in CONDITION_CODES:
                raise ValueError("unknown condition code")
        return conditions


def publish_count(count: int) -> int | None:
    """Suppress a small count and round a publishable one down to a multiple of 5.

    Counts below 10 are not published. 10 and above become the greatest
    multiple of 5 that is still less than or equal to ``count``.

    Args:
        count: A raw cohort size. Zero is allowed and is suppressed.

    Returns:
        The published size, or None when the raw size stays hidden.

    Raises:
        TypeError: ``count`` is not an int. A bool is not an int here.
        ValueError: ``count`` is negative.
    """
    if type(count) is not int:
        raise TypeError("count must be an int")
    if count < 0:
        raise ValueError("count must be zero or greater")
    if count < _PUBLISH_MINIMUM:
        return None
    return (count // _PUBLISH_STEP) * _PUBLISH_STEP
