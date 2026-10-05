"""Personal cabinet overview for the signed-in participant."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.accounts import get_current_user
from app.core.deps import get_cabinet_service
from app.domain.accounts import UserRecord
from app.domain.cabinet_summary import IndexPoint
from app.domain.schemas import (
    CabinetAccountView,
    CabinetConsentsView,
    CabinetHistoryView,
    CabinetIndexPointView,
    CabinetJournalView,
    CabinetMarkerView,
    CabinetView,
)
from app.services.cabinet import CabinetService
from app.services.phenoage import RESEARCH_DISCLAIMER

router = APIRouter(prefix="/api/v1/accounts/me", tags=["cabinet"])


def _point(point: IndexPoint | None) -> CabinetIndexPointView | None:
    if point is None:
        return None
    return CabinetIndexPointView(
        panel_id=point.panel_id,
        observed_on=point.observed_on,
        pheno_age=point.pheno_age,
        age_delta=point.age_delta,
        chronological_age=point.chronological_age,
    )


@router.get("/cabinet", response_model=CabinetView)
async def read_cabinet(
    current: Annotated[UserRecord, Depends(get_current_user)],
    cabinet: Annotated[CabinetService, Depends(get_cabinet_service)],
) -> CabinetView:
    """Return counts, dates and latest values of the owner's own data.

    Describes what is stored. It does not grade values, name a risk, or link
    journal entries to changes in markers.
    """
    overview = await cabinet.overview(current)
    summary = overview.summary
    return CabinetView(
        account=CabinetAccountView(
            public_id=overview.user.public_id,
            created_at=overview.user.created_at,
            email=overview.security.email,
            sign_in_method=overview.security.sign_in_method,
            active_sessions=overview.security.active_sessions,
        ),
        consents=CabinetConsentsView(
            health_data=overview.consents.health_data,
            research_reuse=overview.consents.research_reuse,
            public_sharing=overview.consents.public_sharing,
            sharing_enabled=overview.sharing_enabled,
        ),
        history=CabinetHistoryView(
            panel_count=summary.panel_count,
            first_observed_on=summary.first_observed_on,
            last_observed_on=summary.last_observed_on,
            laboratory_count=summary.laboratory_count,
            scored_count=summary.scored_count,
            repeat_marker_count=summary.repeat_marker_count,
            unmapped_marker_count=summary.unmapped_marker_count,
            latest_missing_markers=list(summary.latest_missing_markers),
        ),
        latest_index=_point(summary.latest_index),
        previous_index=_point(summary.previous_index),
        markers=[
            CabinetMarkerView(
                canonical_id=marker.canonical_id,
                measurements=marker.measurements,
                latest_value=marker.latest_value,
                latest_unit=marker.latest_unit,
                latest_on=marker.latest_on,
                latest_outside_interval=marker.latest_outside_interval,
                in_phenoage=marker.in_phenoage,
            )
            for marker in summary.markers
        ],
        journal=CabinetJournalView(total=summary.journal_total, open=summary.journal_open),
        disclaimer=RESEARCH_DISCLAIMER,
    )
