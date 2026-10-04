"""Public dataset reads. Selects anonymized columns only."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.consents import PUBLIC_SHARING, PUBLIC_SHARING_VERSION
from app.domain.dataset import PublicBiomarkerRow
from app.repositories.models import Biomarker, Consent, LabResult, ShareSettings, User


def public_biomarker_select(
    *, public_id: str | None = None
) -> Select[str, date | None, Decimal | None, str | None, str | None, str, Decimal, str, str]:
    """Build the opt-in confirmed-biomarker query.

    The selected columns are the public contract: pseudonymous ``public_id`` and
    analyte fields. Internal ids, the seed hash, and the document hash are absent.

    Args:
        public_id: When set, restrict the page to that public profile.
    """
    stmt = (
        select(
            User.public_id,
            LabResult.collected_at,
            LabResult.chronological_age,
            Biomarker.loinc_code,
            Biomarker.canonical_name,
            Biomarker.raw_name,
            Biomarker.value,
            Biomarker.unit,
            Biomarker.mapping_status,
        )
        .select_from(Biomarker)
        .join(LabResult, Biomarker.lab_result_id == LabResult.id)
        .join(User, LabResult.user_id == User.id)
        .join(ShareSettings, ShareSettings.user_id == User.id)
        .join(Consent, Consent.user_id == User.id)
        .where(ShareSettings.is_public.is_(True))
        .where(Consent.consent_type == PUBLIC_SHARING)
        .where(Consent.text_version == PUBLIC_SHARING_VERSION)
        .where(Consent.withdrawn_at.is_(None))
        .where(LabResult.confirmed_at.is_not(None))
    )
    if public_id is not None:
        stmt = stmt.where(User.public_id == public_id)
    return stmt.order_by(
        User.public_id.asc(),
        LabResult.collected_at.asc().nulls_last(),
        Biomarker.loinc_code.asc().nulls_last(),
        Biomarker.raw_name.asc(),
    )


def _to_row(record: object) -> PublicBiomarkerRow:
    """Map a selected public row onto the domain record."""
    public_id = record.public_id  # type: ignore[attr-defined]
    collected_at = record.collected_at  # type: ignore[attr-defined]
    chronological_age = record.chronological_age  # type: ignore[attr-defined]
    loinc_code = record.loinc_code  # type: ignore[attr-defined]
    canonical_name = record.canonical_name  # type: ignore[attr-defined]
    raw_name = record.raw_name  # type: ignore[attr-defined]
    value = record.value  # type: ignore[attr-defined]
    unit = record.unit  # type: ignore[attr-defined]
    mapping_status = record.mapping_status  # type: ignore[attr-defined]
    collected = collected_at if isinstance(collected_at, date) or collected_at is None else None
    return PublicBiomarkerRow(
        public_id=str(public_id),
        collected_at=collected,
        chronological_age=(
            chronological_age
            if isinstance(chronological_age, Decimal) or chronological_age is None
            else Decimal(str(chronological_age))
        ),
        loinc_code=None if loinc_code is None else str(loinc_code),
        canonical_name=None if canonical_name is None else str(canonical_name),
        raw_name=str(raw_name),
        value=value if isinstance(value, Decimal) else Decimal(str(value)),
        unit=str(unit),
        mapping_status=str(mapping_status),
    )


class DatasetRepository:
    """Async reads of opted-in confirmed biomarkers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def count_public_biomarkers(self) -> int:
        """Return how many confirmed analyte rows belong to opted-in profiles."""
        filtered = public_biomarker_select().order_by(None).subquery()
        result = await self._session.execute(select(func.count()).select_from(filtered))
        counted = result.scalar_one()
        return int(counted)

    async def list_public_biomarkers(
        self,
        *,
        limit: int,
        offset: int,
    ) -> tuple[PublicBiomarkerRow, ...]:
        """Return one page of public analyte rows.

        Args:
            limit: Maximum rows to return.
            offset: Rows to skip.
        """
        stmt = public_biomarker_select().limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        return tuple(_to_row(record) for record in result.all())

    async def public_profile_exists(self, public_id: str) -> bool:
        """Return True when this public id belongs to an opted-in profile.

        Args:
            public_id: Pseudonymous profile id, never the internal user UUID.
        """
        stmt = (
            select(User.public_id)
            .join(ShareSettings, ShareSettings.user_id == User.id)
            .join(Consent, Consent.user_id == User.id)
            .where(User.public_id == public_id)
            .where(ShareSettings.is_public.is_(True))
            .where(Consent.consent_type == PUBLIC_SHARING)
            .where(Consent.text_version == PUBLIC_SHARING_VERSION)
            .where(Consent.withdrawn_at.is_(None))
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_public_profile_biomarkers(
        self,
        public_id: str,
    ) -> tuple[PublicBiomarkerRow, ...]:
        """Return confirmed analytes for one opted-in profile.

        Args:
            public_id: Pseudonymous profile id.
        """
        result = await self._session.execute(public_biomarker_select(public_id=public_id))
        return tuple(_to_row(record) for record in result.all())
