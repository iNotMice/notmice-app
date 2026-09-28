"""Cohort count suppression and the lab query contract.

Nothing in the API calls this module. The threshold 10 and the step 5 are the
starting values of ``publish_count``. They are not a portal setting: a lab
portal does not exist, and those numbers stay unapproved until the DPIA.
"""

from typing import Annotated, Final

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

# Starting values exercised by the tests. Not portal configuration.
_PUBLISH_MINIMUM: Final = 10
_PUBLISH_STEP: Final = 5
_QUERY_LIMIT: Final = 5
_LABEL_MAX: Final = 120

_Label = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=_LABEL_MAX),
]


class CohortQuery(BaseModel):
    """A closed filter for a future lab cohort. It does not run a search.

    ``markers`` and ``interventions`` each hold at most five labels.
    Any other field is rejected.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    markers: tuple[_Label, ...] = Field(default=(), max_length=_QUERY_LIMIT)
    interventions: tuple[_Label, ...] = Field(default=(), max_length=_QUERY_LIMIT)


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
