"""Overview of a participant's own cabinet. Pure rules; no I/O lives here.

The summary describes what the account holds: how many confirmed panels,
over which period, which markers have repeat measurements, and what the
latest research index was. It never grades a value, names a risk, or links
a journal entry to a change in a marker.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from app.domain.cabinet import PHENOAGE_MARKER_IDS, outside_printed_interval
from app.domain.protocol import ProtocolEntry
from app.domain.uploads import OwnedLabPanel


@dataclass(frozen=True, slots=True)
class ScoredPanel:
    """A confirmed panel with the research index the engine gave it."""

    panel: OwnedLabPanel
    pheno_age: float | None
    age_delta: float | None
    missing_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexPoint:
    """One scored panel on the index timeline."""

    panel_id: UUID
    observed_on: date
    pheno_age: float
    age_delta: float
    chronological_age: float | None


@dataclass(frozen=True, slots=True)
class MarkerSummary:
    """Measurements of one canonical marker across the account."""

    canonical_id: str
    measurements: int
    latest_value: float
    latest_unit: str
    latest_on: date
    latest_outside_interval: bool
    in_phenoage: bool


@dataclass(frozen=True, slots=True)
class CabinetSummary:
    """What the cabinet overview shows. Counts and dates, no judgements."""

    panel_count: int
    first_observed_on: date | None
    last_observed_on: date | None
    laboratory_count: int
    scored_count: int
    latest_index: IndexPoint | None
    previous_index: IndexPoint | None
    latest_missing_markers: tuple[str, ...]
    markers: tuple[MarkerSummary, ...]
    repeat_marker_count: int
    unmapped_marker_count: int
    journal_total: int
    journal_open: int


def observed_on(panel: OwnedLabPanel) -> date:
    """Collection date when the report has one, otherwise the confirmation day."""
    return panel.collected_at if panel.collected_at is not None else panel.confirmed_at.date()


def summarize_cabinet(
    panels: Sequence[ScoredPanel],
    journal: Iterable[ProtocolEntry],
) -> CabinetSummary:
    """Build the overview from the owner's confirmed panels and journal.

    Args:
        panels: Confirmed panels with their index, in any order.
        journal: The owner's journal entries.

    Returns:
        Counts, the observed period, per-marker latest values in dictionary
        order, and the two most recent index points. Panels are ordered by
        observation date, then by confirmation time.
    """
    ordered = sorted(panels, key=lambda item: (observed_on(item.panel), item.panel.confirmed_at))
    entries = tuple(journal)

    scored = [item for item in ordered if item.pheno_age is not None and item.age_delta is not None]
    points = [
        IndexPoint(
            panel_id=item.panel.id,
            observed_on=observed_on(item.panel),
            pheno_age=float(item.pheno_age),
            age_delta=float(item.age_delta),
            chronological_age=(
                float(item.panel.chronological_age)
                if item.panel.chronological_age is not None
                else None
            ),
        )
        for item in scored
        if item.pheno_age is not None and item.age_delta is not None
    ]

    markers = _marker_summaries(item.panel for item in ordered)
    unmapped = sum(
        1 for item in ordered for marker in item.panel.markers if marker.canonical_id is None
    )
    laboratories = {
        item.panel.lab_name.strip().casefold()
        for item in ordered
        if item.panel.lab_name and item.panel.lab_name.strip()
    }

    return CabinetSummary(
        panel_count=len(ordered),
        first_observed_on=observed_on(ordered[0].panel) if ordered else None,
        last_observed_on=observed_on(ordered[-1].panel) if ordered else None,
        laboratory_count=len(laboratories),
        scored_count=len(points),
        latest_index=points[-1] if points else None,
        previous_index=points[-2] if len(points) >= 2 else None,
        latest_missing_markers=ordered[-1].missing_markers if ordered else PHENOAGE_MARKER_IDS,
        markers=markers,
        repeat_marker_count=sum(1 for marker in markers if marker.measurements >= 2),
        unmapped_marker_count=unmapped,
        journal_total=len(entries),
        journal_open=sum(1 for entry in entries if entry.ended_on is None),
    )


def _marker_summaries(panels: Iterable[OwnedLabPanel]) -> tuple[MarkerSummary, ...]:
    """Latest value per canonical marker. Panels arrive oldest first.

    A repeated id on one panel counts once, keeping the first value, the
    same rule ``canonical_marker_values`` uses for scoring.
    """
    counts: dict[str, int] = {}
    latest: dict[str, MarkerSummary] = {}
    for panel in panels:
        seen: set[str] = set()
        for marker in panel.markers:
            canonical_id = marker.canonical_id
            if canonical_id is None or canonical_id in seen:
                continue
            seen.add(canonical_id)
            counts[canonical_id] = counts.get(canonical_id, 0) + 1
            latest[canonical_id] = MarkerSummary(
                canonical_id=canonical_id,
                measurements=counts[canonical_id],
                latest_value=float(marker.value),
                latest_unit=marker.unit,
                latest_on=observed_on(panel),
                latest_outside_interval=outside_printed_interval(
                    marker.value,
                    reference_low=marker.reference_low,
                    reference_high=marker.reference_high,
                    lab_flag=marker.lab_flag,
                ),
                in_phenoage=canonical_id in PHENOAGE_MARKER_IDS,
            )
    levine = [latest[marker_id] for marker_id in PHENOAGE_MARKER_IDS if marker_id in latest]
    others = sorted(
        (summary for marker_id, summary in latest.items() if marker_id not in PHENOAGE_MARKER_IDS),
        key=lambda summary: summary.canonical_id,
    )
    return tuple(levine + others)
