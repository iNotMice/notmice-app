"""Cabinet rules for a confirmed panel. No I/O lives here."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal

_LAB_MARKS = frozenset({"H", "L", "*"})

# Levine 2018 nine, in the LOINC dictionary order.
PHENOAGE_MARKER_IDS: tuple[str, ...] = (
    "albumin",
    "creatinine",
    "glucose",
    "crp",
    "lymphocyte",
    "mcv",
    "rdw",
    "alp",
    "wbc",
)


def outside_printed_interval(
    value: Decimal,
    *,
    reference_low: Decimal | None,
    reference_high: Decimal | None,
    lab_flag: str | None,
) -> bool:
    """Return whether the cabinet shows the neutral out-of-interval flag.

    The flag is set only when ``value`` is strictly below the printed lower
    bound, strictly above the printed upper bound, or the laboratory mark is
    ``H``, ``L``, or ``*``. A missing bound is not a flag. Bounds are inclusive.
    An inverted pair is ignored. The platform window and the dictionary typo
    window are not inputs.

    Args:
        value: Result in the same unit as the stored bounds.
        reference_low: Printed lower bound, or None when the form has none.
        reference_high: Printed upper bound, or None when the form has none.
        lab_flag: Stored laboratory mark, or None.
    """
    if lab_flag in _LAB_MARKS:
        return True
    if reference_low is not None and reference_high is not None and reference_low > reference_high:
        return False
    if reference_low is not None and value < reference_low:
        return True
    if reference_high is not None and value > reference_high:
        return True
    return False


def canonical_marker_values(
    markers: Iterable[tuple[str | None, float]],
) -> dict[str, float]:
    """Return canonical id to value. A repeated id keeps the first value.

    Args:
        markers: Pairs of canonical id and the stored value. ``None`` ids
            are names the dictionary did not map, and they are skipped.
    """
    values: dict[str, float] = {}
    for canonical_id, value in markers:
        if canonical_id is None or canonical_id in values:
            continue
        values[canonical_id] = value
    return values


def missing_phenoage_markers(present_ids: Iterable[str]) -> tuple[str, ...]:
    """Return Levine marker ids that are absent, in dictionary order.

    Args:
        present_ids: Canonical ids on one confirmed panel. Unknown ids are
            ignored. Order and duplicates do not matter.
    """
    present = set(present_ids)
    return tuple(marker_id for marker_id in PHENOAGE_MARKER_IDS if marker_id not in present)
