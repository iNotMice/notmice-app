"""Consent-gated query primitives for aggregate laboratory cohorts."""

from __future__ import annotations

from sqlalchemy import Select, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.selectable import Exists

from app.domain.cohort import publish_count
from app.domain.consents import RESEARCH_REUSE, RESEARCH_REUSE_VERSION
from app.repositories.models import Consent, LabResult, User


def current_research_reuse_granted() -> Exists:
    """Build the active-current-version research consent predicate for a cohort user."""
    return exists(
        select(Consent.id)
        .where(Consent.user_id == User.id)
        .where(Consent.consent_type == RESEARCH_REUSE)
        .where(Consent.text_version == RESEARCH_REUSE_VERSION)
        .where(Consent.withdrawn_at.is_(None))
    )


def eligible_participant_count_select() -> Select[tuple[int]]:
    """Count only participants with current research consent and confirmed panels."""
    has_confirmed_panel = exists(
        select(LabResult.id)
        .where(LabResult.user_id == User.id)
        .where(LabResult.confirmed_at.is_not(None))
    )
    return select(func.count(User.id)).where(
        current_research_reuse_granted(),
        has_confirmed_panel,
    )


class CohortRepository:
    """Internal aggregate eligibility access; never returns participant rows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_eligible_participants(self) -> int | None:
        """Return a suppressed/rounded eligible count, never the raw cohort size."""
        result = await self._session.execute(eligible_participant_count_select())
        return publish_count(int(result.scalar_one()))
