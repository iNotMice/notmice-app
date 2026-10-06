"""Cabinet overview rules: counts, order, latest values. No grading of values."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

from app.domain.cabinet import PHENOAGE_MARKER_IDS
from app.domain.cabinet_summary import ScoredPanel, summarize_cabinet
from app.domain.protocol import ProtocolEntry
from app.domain.uploads import OwnedLabPanel, OwnedMarker
from app.services.cabinet import score_panel

_ALEXEI = {
    "albumin": "42",
    "creatinine": "1.2",
    "glucose": "104",
    "crp": "7.0",
    "lymphocyte": "23",
    "mcv": "92",
    "rdw": "14.0",
    "alp": "80",
    "wbc": "7.4",
}


def _marker(
    canonical_id: str | None,
    value: str,
    *,
    unit: str = "u",
    low: str | None = None,
    high: str | None = None,
    flag: str | None = None,
) -> OwnedMarker:
    return OwnedMarker(
        raw_name=canonical_id or "Unknown analyte",
        canonical_id=canonical_id,
        loinc_code=None,
        value=Decimal(value),
        unit=unit,
        reference_low=None if low is None else Decimal(low),
        reference_high=None if high is None else Decimal(high),
        lab_flag=flag,
    )


def _panel(
    collected_at: date | None,
    markers: tuple[OwnedMarker, ...],
    *,
    lab: str | None = "Lab A",
    age: str | None = "45",
    confirmed_at: datetime | None = None,
) -> OwnedLabPanel:
    return OwnedLabPanel(
        id=uuid4(),
        collected_at=collected_at,
        lab_name=lab,
        chronological_age=None if age is None else Decimal(age),
        confirmed_at=confirmed_at or datetime(2026, 10, 1, 9, 0, tzinfo=UTC),
        document_sha256="a" * 64,
        markers=markers,
    )


def _full(collected_at: date, crp: str = "7.0", age: str = "45") -> OwnedLabPanel:
    values = dict(_ALEXEI, crp=crp)
    return _panel(
        collected_at, tuple(_marker(key, value) for key, value in values.items()), age=age
    )


def _entry(ended_on: date | None) -> ProtocolEntry:
    return ProtocolEntry(
        id=uuid4(),
        kind="activity",
        title="Running",
        dose=None,
        started_on=date(2026, 6, 1),
        ended_on=ended_on,
        note=None,
    )


def test_empty_cabinet_has_no_dates_and_lists_every_missing_marker() -> None:
    summary = summarize_cabinet([], [])
    assert summary.panel_count == 0
    assert summary.first_observed_on is None
    assert summary.last_observed_on is None
    assert summary.latest_index is None
    assert summary.previous_index is None
    assert summary.latest_missing_markers == PHENOAGE_MARKER_IDS
    assert summary.markers == ()


def test_panels_are_ordered_by_collection_date_not_by_input_order() -> None:
    later = score_panel(_full(date(2026, 8, 1), crp="3.0", age="45.3"))
    earlier = score_panel(_full(date(2026, 4, 1)))
    summary = summarize_cabinet([later, earlier], [])
    assert summary.first_observed_on == date(2026, 4, 1)
    assert summary.last_observed_on == date(2026, 8, 1)
    assert summary.scored_count == 2
    assert summary.latest_index is not None
    assert summary.previous_index is not None
    assert summary.latest_index.observed_on == date(2026, 8, 1)
    assert summary.previous_index.observed_on == date(2026, 4, 1)
    assert round(summary.previous_index.pheno_age, 1) == 51.3


def test_confirmation_day_stands_in_for_a_missing_collection_date() -> None:
    panel = _panel(
        None,
        (_marker("albumin", "44"),),
        confirmed_at=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
    )
    summary = summarize_cabinet([score_panel(panel)], [])
    assert summary.last_observed_on == date(2026, 9, 15)


def test_unscored_panel_is_counted_but_not_on_the_index_timeline() -> None:
    partial = _panel(date(2026, 9, 1), (_marker("albumin", "44"), _marker("crp", "1.0")))
    summary = summarize_cabinet([score_panel(partial)], [])
    assert summary.panel_count == 1
    assert summary.scored_count == 0
    assert summary.latest_index is None
    assert "creatinine" in summary.latest_missing_markers
    assert "albumin" not in summary.latest_missing_markers


def test_markers_keep_dictionary_order_count_repeats_and_latest_value() -> None:
    first = _panel(date(2026, 1, 1), (_marker("ferritin", "50"), _marker("crp", "2.0")))
    second = _panel(
        date(2026, 5, 1),
        (_marker("crp", "1.0"), _marker("crp", "9.9"), _marker("albumin", "45")),
    )
    summary = summarize_cabinet([score_panel(second), score_panel(first)], [])
    ids = [marker.canonical_id for marker in summary.markers]
    assert ids == ["albumin", "crp", "ferritin"]
    crp = summary.markers[1]
    assert crp.measurements == 2
    assert crp.latest_value == 1.0
    assert crp.latest_on == date(2026, 5, 1)
    assert crp.in_phenoage is True
    assert summary.markers[2].in_phenoage is False
    assert summary.repeat_marker_count == 1


def test_latest_outside_interval_follows_the_printed_interval_only() -> None:
    panel = _panel(
        date(2026, 2, 1),
        (
            _marker("glucose", "104", low="70", high="99"),
            _marker("albumin", "44"),
            _marker("crp", "0.5", flag="H"),
        ),
    )
    by_id = {
        marker.canonical_id: marker
        for marker in summarize_cabinet([score_panel(panel)], []).markers
    }
    assert by_id["glucose"].latest_outside_interval is True
    assert by_id["albumin"].latest_outside_interval is False
    assert by_id["crp"].latest_outside_interval is True


def test_unmapped_names_and_laboratories_are_counted() -> None:
    one = _panel(date(2026, 1, 1), (_marker(None, "1"), _marker("albumin", "44")), lab="Lab A")
    two = _panel(date(2026, 2, 1), (_marker(None, "2"),), lab=" lab a ")
    three = _panel(date(2026, 3, 1), (_marker("albumin", "45"),), lab="Other Lab")
    four = _panel(date(2026, 4, 1), (_marker("albumin", "46"),), lab=None)
    summary = summarize_cabinet([score_panel(panel) for panel in (one, two, three, four)], [])
    assert summary.unmapped_marker_count == 2
    assert summary.laboratory_count == 2


def test_journal_counts_open_periods() -> None:
    journal = [_entry(None), _entry(date(2026, 7, 1)), _entry(None)]
    summary = summarize_cabinet([], journal)
    assert summary.journal_total == 3
    assert summary.journal_open == 2


def test_scored_panel_keeps_engine_result() -> None:
    scored = score_panel(_full(date(2026, 4, 1)))
    assert isinstance(scored, ScoredPanel)
    assert scored.missing_markers == ()
    assert scored.age_delta is not None
    assert round(scored.age_delta, 1) == 6.3
