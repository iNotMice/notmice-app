"""Tests for cohort validation, privacy thresholds, and route protection."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import cast

import pytest
from fastapi.routing import APIRoute
from pydantic import ValidationError

from app.api.lab_accounts import require_verified_lab
from app.api.lab_cohorts import _marker_view
from app.api.lab_cohorts import router as cohort_router
from app.domain.cohort import CohortQuery, publish_count
from app.domain.conditions import CONDITION_CODES
from app.main import create_app
from app.repositories.cohort import MarkerAggregate

_CONDITION_TOKEN = re.compile(r"^[a-z][a-z0-9_]*$")


def test_publish_count_suppresses_values_below_10() -> None:
    """0 through 9 stay hidden. 10 is large enough to publish."""
    for count in range(10):
        assert publish_count(count) is None
    assert publish_count(10) == 10


def test_publish_count_rounds_down_to_a_multiple_of_5() -> None:
    """14 becomes 10, and 19 becomes 15. An exact multiple stays put."""
    assert publish_count(14) == 10
    assert publish_count(15) == 15
    assert publish_count(19) == 15
    assert publish_count(20) == 20


def test_publish_count_rejects_a_negative_or_a_bool() -> None:
    """A size is a non-negative int. True is not a cohort of one."""
    with pytest.raises(ValueError, match="zero or greater"):
        publish_count(-1)
    with pytest.raises(TypeError, match="int"):
        publish_count(cast(int, True))


def test_cohort_query_accepts_a_closed_filter() -> None:
    """Five dictionary codes, sexes, bands from 18, countries, and draft conditions."""
    conditions = tuple(sorted(CONDITION_CODES)[:10])
    query = CohortQuery.model_validate(
        {
            "markers": ["1751-7", "2160-0", "2345-7", "30522-7", "6690-2"],
            "sex_at_birth": ["female", "male", "intersex", "undisclosed"],
            "age_bands": ["18-29", "30-39", "40-49", "50-59", "60-69", "70-plus"],
            "countries": ["KG", "DE"],
            "conditions": list(conditions),
        }
    )
    assert query.markers == ("1751-7", "2160-0", "2345-7", "30522-7", "6690-2")
    assert query.sex_at_birth == ("female", "male", "intersex", "undisclosed")
    assert query.age_bands[0] == "18-29"
    assert query.age_bands[-1] == "70-plus"
    assert query.countries == ("KG", "DE")
    assert query.conditions == conditions
    empty = CohortQuery()
    assert empty.markers == ()
    assert empty.sex_at_birth == ()
    assert empty.age_bands == ()
    assert empty.countries == ()
    assert empty.conditions == ()
    assert empty.collected_from is None
    assert empty.collected_to is None


def test_cohort_query_accepts_inclusive_collection_date_bounds() -> None:
    query = CohortQuery.model_validate(
        {"collected_from": "2026-01-01", "collected_to": "2026-06-30"}
    )
    assert query.collected_from is not None
    assert query.collected_to is not None
    assert query.collected_from.isoformat() == "2026-01-01"
    assert query.collected_to.isoformat() == "2026-06-30"


def test_cohort_query_rejects_a_reversed_collection_date_range() -> None:
    with pytest.raises(ValidationError, match="on or before"):
        CohortQuery.model_validate(
            {"collected_from": "2026-06-30", "collected_to": "2026-01-01"}
        )


def test_cohort_query_rejects_a_sixth_marker() -> None:
    """A sixth marker is over the limit, even when every code is in the dictionary."""
    six = ["1751-7", "2160-0", "2345-7", "30522-7", "6690-2", "787-2"]
    with pytest.raises(ValidationError, match="at most 5"):
        CohortQuery.model_validate({"markers": six})


def test_cohort_query_rejects_an_unknown_loinc_and_free_text() -> None:
    """A code outside dictionary.v1.json and a plain label are both rejected."""
    for marker in ("99999-9", "albumin", "Walk"):
        with pytest.raises(ValidationError, match="unknown LOINC code"):
            CohortQuery.model_validate({"markers": [marker]})


def test_cohort_query_cannot_express_an_age_under_18() -> None:
    """The youngest band is 18-29. A younger age has no field and no band."""
    for payload in (
        {"age": 17},
        {"age_min": 0},
        {"age_max": 17},
        {"year_of_birth": 2010},
    ):
        with pytest.raises(ValidationError, match="Extra inputs"):
            CohortQuery.model_validate(payload)
    for band in ("0-17", "17", "under-18"):
        with pytest.raises(ValidationError, match="Input should be"):
            CohortQuery.model_validate({"age_bands": [band]})
    with pytest.raises(ValidationError, match="Input should be"):
        CohortQuery.model_validate({"age_bands": ["18-29", "0-17"]})
    with pytest.raises(ValidationError, match="Input should be"):
        CohortQuery.model_validate({"sex_at_birth": ["other"]})


def test_cohort_query_rejects_the_journal_and_any_extra_field() -> None:
    """A journal list and an email field are outside the contract."""
    assert "interventions" not in CohortQuery.model_fields
    with pytest.raises(ValidationError, match="Extra inputs"):
        CohortQuery.model_validate({"interventions": ["Walk", "Magnesium"]})
    with pytest.raises(ValidationError, match="Extra inputs"):
        CohortQuery.model_validate({"markers": ["1751-7"], "email": "a@b.example"})


def test_cohort_statistics_serialize_as_json_numbers() -> None:
    marker = _marker_view(
        MarkerAggregate(
            loinc_code="1751-7",
            canonical_name="Albumin",
            n=10,
            unit="g/L",
            mean=Decimal("3.3"),
            median=Decimal("3.3"),
            p25=Decimal("3.1"),
            p75=Decimal("3.5"),
        )
    )
    payload = marker.model_dump(mode="json")
    assert payload["mean"] == 3.3
    assert isinstance(payload["mean"], float)


def test_draft_condition_codes_are_tokens() -> None:
    """The draft dictionary is a set of tokens, so a label cannot sneak in."""
    assert len(CONDITION_CODES) >= 10
    for code in CONDITION_CODES:
        assert _CONDITION_TOKEN.fullmatch(code), code


def test_cohort_query_rejects_an_unknown_condition_and_an_eleventh() -> None:
    """Ten draft codes fit. An eleventh code, or one outside the list, does not."""
    codes = sorted(CONDITION_CODES)
    assert len(codes) >= 11
    accepted = CohortQuery.model_validate({"conditions": codes[:10]})
    assert accepted.conditions == tuple(codes[:10])
    with pytest.raises(ValidationError, match="at most 10"):
        CohortQuery.model_validate({"conditions": codes[:11]})
    for code in ("not_a_condition", "Type 2 diabetes", "Walk"):
        with pytest.raises(ValidationError, match="unknown condition code"):
            CohortQuery.model_validate({"conditions": [code]})


def test_cohort_query_rejects_a_bad_country_and_a_twenty_first() -> None:
    """A country is two uppercase letters, and the list stops at twenty."""
    twenty = [f"A{chr(ord('A') + index)}" for index in range(20)]
    accepted = CohortQuery.model_validate({"countries": twenty})
    assert accepted.countries == tuple(twenty)
    with pytest.raises(ValidationError, match="at most 20"):
        CohortQuery.model_validate({"countries": [*twenty, "AU"]})
    for country in ("kg", "Kyrgyzstan", "K", "K1", "KG "):
        with pytest.raises(ValidationError):
            CohortQuery.model_validate({"countries": [country]})


def test_cohort_routes_are_mounted_behind_verified_lab_access() -> None:
    app = create_app()
    assert "/api/v1/lab/cohorts/query" in app.openapi()["paths"]
    assert "/api/v1/lab/cohorts/facets" in app.openapi()["paths"]
    routes: dict[str, APIRoute] = {
        route.path: route
        for route in cohort_router.routes
        if isinstance(route, APIRoute)
    }
    query_route = routes["/api/v1/lab/cohorts/query"]
    facets_route = routes["/api/v1/lab/cohorts/facets"]
    assert query_route.methods == {"POST"}
    assert facets_route.methods == {"GET"}
    for route in (query_route, facets_route):
        assert any(
            dependency.call is require_verified_lab
            for dependency in route.dependant.dependencies
        )
