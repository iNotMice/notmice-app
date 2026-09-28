"""The cabinet flag follows the printed interval and the laboratory mark only."""

from __future__ import annotations

from decimal import Decimal

from app.domain.cabinet import outside_printed_interval


def test_flag_only_outside_printed_interval_or_lab_mark() -> None:
    """A value inside the printed interval is quiet, even outside a platform window.

    42 g/L sits outside the platform albumin window 45-50. 8 g/L sits outside
    the dictionary typo window. Neither is a flag without a printed breach or
    an H/L/* mark.
    """
    assert (
        outside_printed_interval(
            Decimal("42"),
            reference_low=Decimal("35"),
            reference_high=Decimal("52"),
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("8"),
            reference_low=None,
            reference_high=None,
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("30"),
            reference_low=Decimal("35"),
            reference_high=Decimal("50"),
            lab_flag=None,
        )
        is True
    )
    assert (
        outside_printed_interval(
            Decimal("2.5"),
            reference_low=Decimal("0"),
            reference_high=Decimal("1"),
            lab_flag=None,
        )
        is True
    )


def test_bounds_are_inclusive_and_one_sided() -> None:
    """Equal to a bound stays inside. An open side flags only past that bound."""
    assert (
        outside_printed_interval(
            Decimal("35"),
            reference_low=Decimal("35"),
            reference_high=Decimal("50"),
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("50"),
            reference_low=Decimal("35"),
            reference_high=Decimal("50"),
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("4"),
            reference_low=None,
            reference_high=Decimal("5"),
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("6"),
            reference_low=None,
            reference_high=Decimal("5"),
            lab_flag=None,
        )
        is True
    )
    assert (
        outside_printed_interval(
            Decimal("11"),
            reference_low=Decimal("10"),
            reference_high=None,
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("9"),
            reference_low=Decimal("10"),
            reference_high=None,
            lab_flag=None,
        )
        is True
    )


def test_lab_mark_flags_even_inside_the_printed_interval() -> None:
    """H, L, and * are the laboratory's own mark. Other text is not."""
    inside = {
        "reference_low": Decimal("20"),
        "reference_high": Decimal("40"),
    }
    assert outside_printed_interval(Decimal("32"), lab_flag="H", **inside) is True
    assert outside_printed_interval(Decimal("32"), lab_flag="L", **inside) is True
    assert outside_printed_interval(Decimal("32"), lab_flag="*", **inside) is True
    assert outside_printed_interval(Decimal("32"), lab_flag=None, **inside) is False
    assert outside_printed_interval(Decimal("32"), lab_flag="high", **inside) is False
    assert outside_printed_interval(Decimal("32"), lab_flag="", **inside) is False


def test_inverted_bounds_do_not_flag() -> None:
    """A swapped pair is not an interval. Only a laboratory mark still flags."""
    assert (
        outside_printed_interval(
            Decimal("7"),
            reference_low=Decimal("10"),
            reference_high=Decimal("5"),
            lab_flag=None,
        )
        is False
    )
    assert (
        outside_printed_interval(
            Decimal("7"),
            reference_low=Decimal("10"),
            reference_high=Decimal("5"),
            lab_flag="H",
        )
        is True
    )
