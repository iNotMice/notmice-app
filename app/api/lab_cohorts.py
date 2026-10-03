"""Verified-laboratory aggregate cohort endpoints."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.lab_accounts import require_verified_lab
from app.core.deps import get_cohort_repository
from app.domain.cohort import CohortQuery
from app.domain.lab_accounts import LabUserRecord
from app.domain.pii import reject_sensitive_output
from app.domain.schemas import (
    CohortFacet,
    CohortFacetsResponse,
    CohortMarkerAggregate,
    CohortQueryResponse,
)
from app.repositories.cohort import CohortAggregate, CohortFacets, CohortRepository, MarkerAggregate

router = APIRouter(prefix="/api/v1/lab/cohorts", tags=["laboratory cohorts"])


def _marker_view(marker: MarkerAggregate) -> CohortMarkerAggregate:
    """Convert one aggregate-only repository row into its public schema."""

    def json_number(value: Decimal | None) -> float | None:
        return None if value is None else float(value)

    return CohortMarkerAggregate(
        loinc_code=marker.loinc_code,
        canonical_name=marker.canonical_name,
        n=marker.n,
        unit=marker.unit,
        mean=json_number(marker.mean),
        median=json_number(marker.median),
        p25=json_number(marker.p25),
        p75=json_number(marker.p75),
    )


def _cohort_view(result: CohortAggregate) -> CohortQueryResponse:
    return CohortQueryResponse(
        cohort_size=result.cohort_size,
        markers=[_marker_view(marker) for marker in result.markers],
        suppressed=result.suppressed,
    )


def _facets_view(result: CohortFacets) -> CohortFacetsResponse:
    return CohortFacetsResponse(
        sex_at_birth=[
            CohortFacet(value=value, count=count) for value, count in result.sex_at_birth
        ],
        age_bands=[CohortFacet(value=value, count=count) for value, count in result.age_bands],
        countries=[CohortFacet(value=value, count=count) for value, count in result.countries],
        conditions=[CohortFacet(value=value, count=count) for value, count in result.conditions],
        markers=[CohortFacet(value=value, count=count) for value, count in result.markers],
    )


def _rate_limited() -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "The organization's daily cohort-query budget is exhausted"},
    )


@router.post(
    "/query",
    response_model=CohortQueryResponse,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Daily query budget exhausted"}},
)
async def query_cohort(
    payload: CohortQuery,
    user: Annotated[LabUserRecord, Depends(require_verified_lab)],
    repository: Annotated[CohortRepository, Depends(get_cohort_repository)],
) -> CohortQueryResponse | JSONResponse:
    """Return a consent-gated cohort count and safe marker aggregates."""
    result = await repository.query(
        lab_user_id=user.id,
        organization_id=user.organization_id,
        query=payload,
    )
    if result is None:
        return _rate_limited()
    response = _cohort_view(result)
    reject_sensitive_output(response.model_dump(mode="json"))
    return response


@router.get(
    "/facets",
    response_model=CohortFacetsResponse,
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Daily query budget exhausted"}},
)
async def cohort_facets(
    user: Annotated[LabUserRecord, Depends(require_verified_lab)],
    repository: Annotated[CohortRepository, Depends(get_cohort_repository)],
) -> CohortFacetsResponse | JSONResponse:
    """Return only facet values with at least ten eligible participants."""
    result = await repository.facets(
        lab_user_id=user.id,
        organization_id=user.organization_id,
    )
    if result is None:
        return _rate_limited()
    response = _facets_view(result)
    reject_sensitive_output(response.model_dump(mode="json"))
    return response
