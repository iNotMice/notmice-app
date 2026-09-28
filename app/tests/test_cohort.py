"""publish_count and CohortQuery. No route serves either one."""

from __future__ import annotations

from typing import cast

import pytest
from pydantic import ValidationError

from app.domain.cohort import CohortQuery, publish_count
from app.main import create_app


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


def test_cohort_query_accepts_five_markers_and_five_interventions() -> None:
    """The closed contract keeps both lists when each has five labels."""
    query = CohortQuery.model_validate(
        {
            "markers": ["1751-7", "2160-0", "2345-7", "30522-7", "6690-2"],
            "interventions": ["Walk", "Magnesium", "Sleep", "Creatine", "Zone 2"],
        }
    )
    assert len(query.markers) == 5
    assert query.interventions[1] == "Magnesium"


def test_cohort_query_rejects_extra_fields() -> None:
    """A field outside markers and interventions is not part of the contract."""
    with pytest.raises(ValidationError, match="Extra inputs"):
        CohortQuery.model_validate({"markers": ["1751-7"], "email": "a@b.example"})
    with pytest.raises(ValidationError, match="Extra inputs"):
        CohortQuery.model_validate({"age": 40})


def test_cohort_query_rejects_more_than_five_markers_or_interventions() -> None:
    """A sixth marker or a sixth intervention is rejected."""
    six = ["a", "b", "c", "d", "e", "f"]
    with pytest.raises(ValidationError, match="at most 5"):
        CohortQuery.model_validate({"markers": six})
    with pytest.raises(ValidationError, match="at most 5"):
        CohortQuery.model_validate({"interventions": six})


def test_app_has_no_cohort_route() -> None:
    """The contract is not mounted. There is no lab-portal endpoint."""
    paths = {getattr(route, "path", "") for route in create_app().routes}
    assert not any("cohort" in path for path in paths)
