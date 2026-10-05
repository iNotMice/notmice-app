"""Personal cabinet overview: one read that gathers the owner's own data.

No new data is collected here. The service reads confirmed panels, the
journal, consents and sign-in material that already belong to the account,
scores panels with the same engine as the history, and summarizes them.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.accounts import AccountSecurity, ConsentRecord, UserRecord
from app.domain.cabinet import canonical_marker_values
from app.domain.cabinet_summary import CabinetSummary, ScoredPanel, summarize_cabinet
from app.domain.consents import (
    HEALTH_DATA,
    HEALTH_DATA_VERSION,
    PUBLIC_SHARING,
    PUBLIC_SHARING_VERSION,
    RESEARCH_REUSE,
    RESEARCH_REUSE_VERSION,
)
from app.domain.uploads import OwnedLabPanel
from app.services.accounts import AccountService
from app.services.phenoage import score_confirmed_panel
from app.services.protocol import ProtocolService
from app.services.uploads import UploadService


@dataclass(frozen=True, slots=True)
class ConsentState:
    """Whether the current text version of each consent is active."""

    health_data: bool
    research_reuse: bool
    public_sharing: bool


@dataclass(frozen=True, slots=True)
class CabinetOverview:
    """Everything the cabinet overview page needs in one response."""

    user: UserRecord
    security: AccountSecurity
    consents: ConsentState
    sharing_enabled: bool
    summary: CabinetSummary


def _active(rows: tuple[ConsentRecord, ...], consent_type: str, version: str) -> bool:
    return any(
        row.consent_type == consent_type
        and row.text_version == version
        and row.withdrawn_at is None
        for row in rows
    )


def score_panel(panel: OwnedLabPanel) -> ScoredPanel:
    """Score one confirmed panel exactly as the history endpoint does."""
    age = float(panel.chronological_age) if panel.chronological_age is not None else None
    result = score_confirmed_panel(
        canonical_marker_values(
            (marker.canonical_id, float(marker.value)) for marker in panel.markers
        ),
        chronological_age=age,
    )
    return ScoredPanel(
        panel=panel,
        pheno_age=result.pheno_age,
        age_delta=result.age_delta,
        missing_markers=result.missing_markers,
    )


class CabinetService:
    """Read-only overview of the signed-in participant's own data."""

    def __init__(
        self,
        *,
        accounts: AccountService,
        uploads: UploadService,
        protocol: ProtocolService,
    ) -> None:
        self._accounts = accounts
        self._uploads = uploads
        self._protocol = protocol

    async def overview(self, user: UserRecord) -> CabinetOverview:
        """Collect and summarize the owner's panels, journal, consents and sign-in.

        Args:
            user: Authenticated participant.
        """
        panels = await self._uploads.list_confirmed(user.id)
        journal = await self._protocol.list_entries(user.id)
        consents = await self._accounts.list_consents(user.id)
        security = await self._accounts.security_overview(user.id)
        state = ConsentState(
            health_data=_active(consents, HEALTH_DATA, HEALTH_DATA_VERSION),
            research_reuse=_active(consents, RESEARCH_REUSE, RESEARCH_REUSE_VERSION),
            public_sharing=_active(consents, PUBLIC_SHARING, PUBLIC_SHARING_VERSION),
        )
        return CabinetOverview(
            user=user,
            security=security,
            consents=state,
            sharing_enabled=user.is_public and state.public_sharing,
            summary=summarize_cabinet([score_panel(panel) for panel in panels], journal),
        )
