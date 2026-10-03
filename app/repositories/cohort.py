"""Consent-gated aggregate laboratory cohort queries."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

import structlog
from sqlalchemy import Select, distinct, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.sql.selectable import Exists, Subquery

from app.domain.cohort import CohortQuery, publish_count
from app.domain.consents import RESEARCH_REUSE, RESEARCH_REUSE_VERSION
from app.repositories.models import (
    Biomarker,
    Consent,
    LabQueryAudit,
    LabResult,
    Organization,
    ParticipantProfileRow,
    ProfileCondition,
    User,
)

_DAILY_QUERY_LIMIT = 200
_STATISTIC_QUANTUM = Decimal("0.1")
_DIFFERENCING_LOOKBACK = timedelta(minutes=15)
_DIFFERENCING_ALERT_THRESHOLD = 5

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class MarkerAggregate:
    """A marker summary with statistics omitted below the k threshold."""

    loinc_code: str
    canonical_name: str | None
    n: int | None
    unit: str | None
    mean: Decimal | None
    median: Decimal | None
    p25: Decimal | None
    p75: Decimal | None


@dataclass(frozen=True, slots=True)
class CohortAggregate:
    """Published cohort size and marker summaries."""

    cohort_size: int | None
    markers: tuple[MarkerAggregate, ...]
    suppressed: bool


@dataclass(frozen=True, slots=True)
class CohortFacets:
    """Only facet values whose participant count meets the publication threshold."""

    sex_at_birth: tuple[tuple[str, int], ...]
    age_bands: tuple[tuple[str, int], ...]
    countries: tuple[tuple[str, int], ...]
    conditions: tuple[tuple[str, int], ...]
    markers: tuple[tuple[str, int], ...]


def current_research_reuse_granted() -> Exists:
    """Build the active-current-version research consent predicate."""
    return exists(
        select(Consent.id)
        .where(Consent.user_id == User.id)
        .where(Consent.consent_type == RESEARCH_REUSE)
        .where(Consent.text_version == RESEARCH_REUSE_VERSION)
        .where(Consent.withdrawn_at.is_(None))
    )


def _confirmed_panel_exists(query: CohortQuery | None = None) -> Exists:
    """Require a confirmed panel, optionally collected within a date range."""
    statement = (
        select(LabResult.id)
        .where(LabResult.user_id == User.id)
        .where(LabResult.confirmed_at.is_not(None))
    )
    if query is not None:
        if query.collected_from is not None:
            statement = statement.where(LabResult.collected_at >= query.collected_from)
        if query.collected_to is not None:
            statement = statement.where(LabResult.collected_at <= query.collected_to)
    return exists(statement.correlate(User))


def _age_band_predicate(band: str, current_year: int) -> ColumnElement[bool]:
    """Translate a closed adult band into a bounded birth-year expression."""
    birth_year = ParticipantProfileRow.year_of_birth
    if band == "70-plus":
        return birth_year.between(current_year - 120, current_year - 70)
    youngest, oldest = (int(part) for part in band.split("-"))
    return birth_year.between(current_year - oldest, current_year - youngest)


def _eligible_user_predicates(
    query: CohortQuery | None,
    *,
    current_year: int,
) -> tuple[ColumnElement[bool], ...]:
    """Apply current consent, confirmed data, and optional closed profile filters."""
    predicates: list[ColumnElement[bool]] = [
        current_research_reuse_granted(),
        _confirmed_panel_exists(query),
    ]
    if query is None:
        return tuple(predicates)
    if query.sex_at_birth:
        predicates.append(
            exists(
                select(ParticipantProfileRow.id)
                .where(ParticipantProfileRow.user_id == User.id)
                .where(ParticipantProfileRow.sex_at_birth.in_(query.sex_at_birth))
            )
        )
    if query.age_bands:
        predicates.append(
            exists(
                select(ParticipantProfileRow.id)
                .where(ParticipantProfileRow.user_id == User.id)
                .where(
                    or_(
                        *(
                            _age_band_predicate(band, current_year)
                            for band in query.age_bands
                        )
                    )
                )
            )
        )
    if query.countries:
        predicates.append(
            exists(
                select(ParticipantProfileRow.id)
                .where(ParticipantProfileRow.user_id == User.id)
                .where(ParticipantProfileRow.country.in_(query.countries))
            )
        )
    if query.conditions:
        predicates.append(
            exists(
                select(ProfileCondition.id)
                .where(ProfileCondition.user_id == User.id)
                .where(ProfileCondition.code.in_(query.conditions))
            )
        )
    return tuple(predicates)


def eligible_participant_count_select(
    query: CohortQuery | None = None,
    *,
    current_year: int | None = None,
) -> Select[tuple[int]]:
    """Count eligible participants without ever returning their rows."""
    year = current_year if current_year is not None else datetime.now(UTC).year
    return select(func.count(User.id)).where(
        *_eligible_user_predicates(query, current_year=year)
    )


def _date_predicates(query: CohortQuery) -> tuple[ColumnElement[bool], ...]:
    predicates: list[ColumnElement[bool]] = [LabResult.confirmed_at.is_not(None)]
    if query.collected_from is not None:
        predicates.append(LabResult.collected_at >= query.collected_from)
    if query.collected_to is not None:
        predicates.append(LabResult.collected_at <= query.collected_to)
    return tuple(predicates)


def _ranked_marker_query(
    query: CohortQuery,
    *,
    current_year: int,
) -> Subquery:
    """Select each participant's newest in-range observation for each marker."""
    statement = (
        select(
            LabResult.user_id.label("user_id"),
            Biomarker.loinc_code.label("loinc_code"),
            Biomarker.canonical_name.label("canonical_name"),
            Biomarker.value.label("value"),
            Biomarker.unit.label("unit"),
            func.row_number()
            .over(
                partition_by=(LabResult.user_id, Biomarker.loinc_code),
                order_by=(
                    LabResult.collected_at.desc().nulls_last(),
                    LabResult.created_at.desc(),
                    LabResult.id.desc(),
                    Biomarker.id.desc(),
                ),
            )
            .label("observation_rank"),
        )
        .select_from(User)
        .join(LabResult, LabResult.user_id == User.id)
        .join(Biomarker, Biomarker.lab_result_id == LabResult.id)
        .where(*_eligible_user_predicates(query, current_year=current_year))
        .where(*_date_predicates(query))
        .where(Biomarker.mapping_status == "mapped")
        .where(Biomarker.loinc_code.is_not(None))
    )
    if query.markers:
        statement = statement.where(Biomarker.loinc_code.in_(query.markers))
    return statement.subquery("ranked_cohort_markers")


def _rounded_statistic(value: object) -> Decimal:
    """Round a SQL numeric statistic to one decimal place."""
    return Decimal(str(value)).quantize(_STATISTIC_QUANTUM, rounding=ROUND_HALF_UP)


class CohortRepository:
    """Expose only suppressed aggregate results and non-identifying facet values."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def query(
        self,
        *,
        lab_user_id: UUID,
        organization_id: UUID,
        query: CohortQuery,
        now: datetime | None = None,
    ) -> CohortAggregate | None:
        """Return aggregates or ``None`` when the organization's daily budget is full."""
        timestamp = now or datetime.now(UTC)
        audit, allowed = await self._start_audited_query(
            lab_user_id=lab_user_id,
            organization_id=organization_id,
            endpoint="cohorts/query",
            query=query.model_dump(mode="json"),
            now=timestamp,
        )
        if not allowed:
            return None

        raw_cohort_size = int(
            (
                await self._session.execute(
                    eligible_participant_count_select(
                        query,
                        current_year=timestamp.year,
                    )
                )
            ).scalar_one()
        )
        published_size = publish_count(raw_cohort_size)
        audit.result_cohort_size = published_size
        if published_size is None:
            return CohortAggregate(
                cohort_size=None,
                markers=(),
                suppressed=True,
            )

        if published_size <= 20:
            await self._warn_on_narrow_queries(
                organization_id=organization_id,
                query=query.model_dump(mode="json"),
                now=timestamp,
            )

        marker_results: tuple[MarkerAggregate, ...] = ()
        if query.markers:
            marker_results = await self._marker_aggregates(query, timestamp)
        return CohortAggregate(
            cohort_size=published_size,
            markers=marker_results,
            suppressed=False,
        )

    async def facets(
        self,
        *,
        lab_user_id: UUID,
        organization_id: UUID,
        now: datetime | None = None,
    ) -> CohortFacets | None:
        """Return only filter values with at least ten eligible participants."""
        timestamp = now or datetime.now(UTC)
        audit, allowed = await self._start_audited_query(
            lab_user_id=lab_user_id,
            organization_id=organization_id,
            endpoint="cohorts/facets",
            query={},
            now=timestamp,
        )
        if not allowed:
            return None

        current_year = timestamp.year
        eligible = _eligible_user_predicates(None, current_year=current_year)
        count_statement = eligible_participant_count_select(
            current_year=current_year
        )
        raw_size = int((await self._session.execute(count_statement)).scalar_one())
        audit.result_cohort_size = publish_count(raw_size)

        sex_counts = await self._grouped_profile_counts(
            ParticipantProfileRow.sex_at_birth,
            eligible,
        )
        country_counts = await self._grouped_profile_counts(
            ParticipantProfileRow.country,
            eligible,
        )
        condition_counts = await self._session.execute(
            select(
                ProfileCondition.code,
                func.count(distinct(User.id)),
            )
            .join(ProfileCondition, ProfileCondition.user_id == User.id)
            .where(*eligible)
            .group_by(ProfileCondition.code)
        )
        condition_rows = [(row[0], int(row[1])) for row in condition_counts.all()]
        age_counts: list[tuple[str, int]] = []
        for band in ("18-29", "30-39", "40-49", "50-59", "60-69", "70-plus"):
            age_filter = exists(
                select(ParticipantProfileRow.id)
                .where(ParticipantProfileRow.user_id == User.id)
                .where(_age_band_predicate(band, current_year))
            )
            result = await self._session.execute(
                select(func.count(User.id)).where(*eligible, age_filter)
            )
            age_counts.append((band, int(result.scalar_one())))

        marker_rows = await self._session.execute(
            select(
                Biomarker.loinc_code,
                func.count(distinct(LabResult.user_id)),
            )
            .join(LabResult, LabResult.id == Biomarker.lab_result_id)
            .join(User, User.id == LabResult.user_id)
            .where(*eligible)
            .where(LabResult.confirmed_at.is_not(None))
            .where(Biomarker.mapping_status == "mapped")
            .where(Biomarker.loinc_code.is_not(None))
            .group_by(Biomarker.loinc_code)
        )
        marker_counts = [(row[0], int(row[1])) for row in marker_rows.all()]
        return CohortFacets(
            sex_at_birth=self._publish_facets(sex_counts),
            age_bands=self._publish_facets(age_counts),
            countries=self._publish_facets(country_counts),
            conditions=self._publish_facets(condition_rows),
            markers=self._publish_facets(marker_counts),
        )

    async def _grouped_profile_counts(
        self,
        column: InstrumentedAttribute[str | None],
        eligible: tuple[ColumnElement[bool], ...],
    ) -> list[tuple[str | None, int]]:
        result = await self._session.execute(
            select(column, func.count(User.id))
            .join(ParticipantProfileRow, ParticipantProfileRow.user_id == User.id)
            .where(*eligible)
            .where(column.is_not(None))
            .group_by(column)
        )
        return [(row[0], int(row[1])) for row in result.all()]

    @staticmethod
    def _publish_facets(
        rows: Sequence[tuple[str | None, int]],
    ) -> tuple[tuple[str, int], ...]:
        published: list[tuple[str, int]] = []
        for value, raw_count in rows:
            if value is None:
                continue
            count = publish_count(int(raw_count))
            if count is not None:
                published.append((value, count))
        return tuple(sorted(published))

    async def _warn_on_narrow_queries(
        self,
        *,
        organization_id: UUID,
        query: dict[str, object],
        now: datetime,
    ) -> None:
        """Warn internally on repeated near-identical queries over small cohorts."""
        recent = await self._session.execute(
            select(LabQueryAudit.query)
            .where(LabQueryAudit.organization_id == organization_id)
            .where(LabQueryAudit.endpoint == "cohorts/query")
            .where(LabQueryAudit.result_cohort_size.between(10, 20))
            .where(LabQueryAudit.created_at >= now - _DIFFERENCING_LOOKBACK)
            .order_by(LabQueryAudit.created_at.desc())
        )
        similar_count = sum(
            1
            for (previous_query,) in recent.all()
            if isinstance(previous_query, dict)
            and _differs_by_one_filter(query, previous_query)
        )
        if similar_count >= _DIFFERENCING_ALERT_THRESHOLD - 1:
            logger.warning(
                "lab_cohort_differencing_pattern",
                organization_id=str(organization_id),
                recent_similar_queries=similar_count + 1,
            )

    async def _marker_aggregates(
        self,
        query: CohortQuery,
        now: datetime,
    ) -> tuple[MarkerAggregate, ...]:
        ranked = _ranked_marker_query(query, current_year=now.year)
        rows = await self._session.execute(
            select(
                ranked.c.loinc_code,
                func.max(ranked.c.canonical_name),
                ranked.c.unit,
                func.count(),
                func.avg(ranked.c.value),
                func.percentile_cont(0.5).within_group(ranked.c.value),
                func.percentile_cont(0.25).within_group(ranked.c.value),
                func.percentile_cont(0.75).within_group(ranked.c.value),
            )
            .where(ranked.c.observation_rank == 1)
            .group_by(ranked.c.loinc_code, ranked.c.unit)
            .order_by(ranked.c.loinc_code, ranked.c.unit)
        )
        aggregates: list[MarkerAggregate] = []
        for code, canonical_name, unit, raw_n, mean, median, p25, p75 in rows:
            n = int(raw_n)
            published_n = publish_count(n)
            if published_n is None:
                aggregates.append(
                    MarkerAggregate(
                        loinc_code=str(code),
                        canonical_name=canonical_name,
                        n=None,
                        unit=unit,
                        mean=None,
                        median=None,
                        p25=None,
                        p75=None,
                    )
                )
                continue
            aggregates.append(
                MarkerAggregate(
                    loinc_code=str(code),
                    canonical_name=canonical_name,
                    n=published_n,
                    unit=unit,
                    mean=_rounded_statistic(mean),
                    median=_rounded_statistic(median),
                    p25=_rounded_statistic(p25),
                    p75=_rounded_statistic(p75),
                )
            )
        return tuple(aggregates)

    async def _start_audited_query(
        self,
        *,
        lab_user_id: UUID,
        organization_id: UUID,
        endpoint: str,
        query: dict[str, object],
        now: datetime,
    ) -> tuple[LabQueryAudit, bool]:
        """Serialize each organization's budget check and persist its audit entry."""
        organization = await self._session.execute(
            select(Organization.id)
            .where(Organization.id == organization_id)
            .with_for_update()
        )
        if organization.scalar_one_or_none() is None:
            raise ValueError("Verified laboratory organization no longer exists")

        midnight = datetime.combine(now.date(), time.min, tzinfo=UTC)
        tomorrow = midnight + timedelta(days=1)
        used = int(
            (
                await self._session.execute(
                    select(func.count(LabQueryAudit.id))
                    .where(LabQueryAudit.organization_id == organization_id)
                    .where(LabQueryAudit.created_at >= midnight)
                    .where(LabQueryAudit.created_at < tomorrow)
                )
            ).scalar_one()
        )
        audit = LabQueryAudit(
            id=uuid4(),
            lab_user_id=lab_user_id,
            organization_id=organization_id,
            endpoint=endpoint,
            query=query,
        )
        self._session.add(audit)
        await self._session.flush()
        return audit, used < _DAILY_QUERY_LIMIT


def _differs_by_one_filter(
    current: dict[str, object],
    previous: dict[str, object],
) -> bool:
    """Compare normalized closed filters without logging their values."""
    current_values = {key: value for key, value in current.items() if value}
    previous_values = {key: value for key, value in previous.items() if value}
    keys = current_values.keys() | previous_values.keys()
    return sum(current_values.get(key) != previous_values.get(key) for key in keys) == 1
