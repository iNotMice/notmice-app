"""Cabinet rules for a confirmed analyte. No I/O lives here."""

from __future__ import annotations

from decimal import Decimal

_LAB_MARKS = frozenset({"H", "L", "*"})


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
