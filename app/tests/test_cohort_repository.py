"""Tests for the current research-consent cohort gate."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import UTC, datetime
from decimal import Decimal
from typing import cast
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import configure_mappers

from app.domain.cohort import CohortQuery
from app.repositories.cohort import (
    CohortRepository,
    _differs_by_one_filter,
    _ranked_marker_query,
    eligible_participant_count_select,
)
from app.repositories.models import Base


class _Result:
    def __init__(
        self,
        *,
        scalar: int | None = None,
        scalar_or_none: object | None = None,
        rows: tuple[tuple[object, ...], ...] = (),
    ) -> None:
        self._scalar = scalar
        self._scalar_or_none = scalar_or_none
        self._rows = rows

    def scalar_one(self) -> int:
        assert self._scalar is not None
        return self._scalar

    def scalar_one_or_none(self) -> object | None:
        return self._scalar_or_none

    def all(self) -> tuple[tuple[object, ...], ...]:
        return self._rows

    def __iter__(self) -> Iterator[tuple[object, ...]]:
        return iter(self._rows)


def _fake_repository(*results: _Result) -> tuple[CohortRepository, Mock]:
    session = Mock()
    session.execute = AsyncMock(side_effect=results)
    session.flush = AsyncMock()
    session.add = Mock()
    return CohortRepository(cast(AsyncSession, session)), session


def test_lab_identity_tables_are_registered_with_separate_foreign_keys() -> None:
    """Lab identity metadata stays independent of participant credential tables."""
    configure_mappers()
    expected = {
        "organizations",
        "lab_users",
        "lab_sessions",
        "lab_auth_tokens",
        "lab_query_audit",
    }
    assert expected.issubset(Base.metadata.tables)
    lab_user_fks = Base.metadata.tables["lab_users"].foreign_keys
    assert {foreign_key.target_fullname for foreign_key in lab_user_fks} == {
        "organizations.id"
    }


def test_aggregate_eligibility_requires_current_unwithdrawn_research_consent() -> None:
    """The cohort count never uses public-sharing state as research consent."""
    statement = eligible_participant_count_select()
    query = str(statement)

    assert "consents.consent_type" in query
    assert "consents.text_version" in query
    assert "consents.withdrawn_at IS NULL" in query
    assert "lab_results.confirmed_at IS NOT NULL" in query
    assert "share_settings" not in query


def test_aggregate_eligibility_applies_date_and_profile_filters() -> None:
    query = CohortQuery.model_validate(
        {
            "sex_at_birth": ["female"],
            "age_bands": ["30-39"],
            "countries": ["DE"],
            "conditions": ["hypertension"],
            "collected_from": "2025-01-01",
            "collected_to": "2025-12-31",
        }
    )
    sql = str(eligible_participant_count_select(query, current_year=2026))

    assert "lab_results.collected_at >=" in sql
    assert "lab_results.collected_at <=" in sql
    assert "participant_profiles.sex_at_birth IN" in sql
    assert "profile_conditions.code IN" in sql


def test_marker_query_ranks_latest_confirmed_observation_per_participant() -> None:
    query = CohortQuery.model_validate(
        {
            "markers": ["1751-7"],
            "collected_from": "2025-01-01",
            "collected_to": "2025-12-31",
        }
    )
    sql = str(_ranked_marker_query(query, current_year=2026))

    assert "row_number() OVER (PARTITION BY lab_results.user_id, biomarkers.loinc_code" in sql
    assert "lab_results.collected_at DESC NULLS LAST" in sql
    assert "biomarkers.mapping_status =" in sql
    assert "biomarkers.loinc_code IN" in sql
    assert "lab_results.collected_at >=" in sql
    assert "lab_results.collected_at <=" in sql


def test_narrow_query_detector_only_matches_one_changed_filter() -> None:
    assert _differs_by_one_filter(
        {"countries": ["DE"], "markers": ["1751-7"]},
        {"countries": ["FR"], "markers": ["1751-7"]},
    )
    assert not _differs_by_one_filter(
        {"countries": ["DE"], "markers": ["1751-7"]},
        {"countries": ["FR"], "markers": ["2160-0"]},
    )
    assert not _differs_by_one_filter(
        {"countries": ["DE"], "markers": ["1751-7"]},
        {"countries": ["DE"], "markers": ["1751-7"]},
    )


@pytest.mark.asyncio
async def test_small_cohort_suppresses_marker_statistics_and_audit_count() -> None:
    lab_user_id = uuid4()
    organization_id = uuid4()
    repository, session = _fake_repository(
        _Result(scalar_or_none=organization_id),
        _Result(scalar=0),
        _Result(scalar=9),
    )

    result = await repository.query(
        lab_user_id=lab_user_id,
        organization_id=organization_id,
        query=CohortQuery(markers=("1751-7",)),
        now=datetime(2026, 10, 3, tzinfo=UTC),
    )

    assert result is not None
    assert result.cohort_size is None
    assert result.markers == ()
    assert result.suppressed
    audit = session.add.call_args.args[0]
    assert audit.result_cohort_size is None
    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_marker_statistics_are_suppressed_when_marker_count_is_below_ten() -> None:
    lab_user_id = uuid4()
    organization_id = uuid4()
    repository, session = _fake_repository(
        _Result(scalar_or_none=organization_id),
        _Result(scalar=0),
        _Result(scalar=12),
        _Result(rows=()),
        _Result(
            rows=(
                (
                    "1751-7",
                    "Albumin",
                    "g/L",
                    9,
                    Decimal("3.33"),
                    Decimal("3.30"),
                    Decimal("3.10"),
                    Decimal("3.50"),
                ),
            )
        ),
    )

    result = await repository.query(
        lab_user_id=lab_user_id,
        organization_id=organization_id,
        query=CohortQuery(markers=("1751-7",)),
        now=datetime(2026, 10, 3, tzinfo=UTC),
    )

    assert result is not None
    assert result.cohort_size == 10
    assert not result.suppressed
    assert len(result.markers) == 1
    marker = result.markers[0]
    assert marker.n is None
    assert marker.mean is None
    assert marker.median is None
    assert marker.p25 is None
    assert marker.p75 is None
    audit = session.add.call_args.args[0]
    assert audit.result_cohort_size == 10


@pytest.mark.asyncio
async def test_daily_budget_is_checked_and_blocked_attempt_is_audited() -> None:
    lab_user_id = uuid4()
    organization_id = uuid4()
    repository, session = _fake_repository(
        _Result(scalar_or_none=organization_id),
        _Result(scalar=200),
    )

    result = await repository.query(
        lab_user_id=lab_user_id,
        organization_id=organization_id,
        query=CohortQuery(),
        now=datetime(2026, 10, 3, tzinfo=UTC),
    )

    assert result is None
    assert session.add.call_count == 1
    assert session.flush.await_count == 1
    assert session.execute.await_count == 2
