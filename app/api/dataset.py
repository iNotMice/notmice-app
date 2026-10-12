"""Read-only public dataset. Writes are not exposed on these routes."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status

from app.core.config import get_settings
from app.core.deps import get_dataset_service, get_public_rate_limiter
from app.core.rate_limit import SlidingWindowRateLimiter, resolve_client_key
from app.domain.dataset import (
    ProfileNotPublicError,
    PublicBiomarkerRow,
    PublicDatasetPage,
    PublicTimeseries,
    published_chronological_age,
)
from app.domain.pii import PIIValidationError, reject_sensitive_output
from app.domain.schemas import (
    DatasetResponse,
    PublicBiomarkerView,
    TimeseriesMarkerView,
    TimeseriesPointView,
    TimeseriesResponse,
)
from app.services.dataset import DatasetService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["dataset"])


def _number(value: Decimal | None) -> float | None:
    """Convert an optional numeric column to a JSON number."""
    if value is None:
        return None
    return float(value)


def _marker_view(row: PublicBiomarkerRow) -> PublicBiomarkerView:
    """Map a domain row onto the public response model."""
    return PublicBiomarkerView(
        public_id=row.public_id,
        collected_at=row.collected_at,
        chronological_age=_number(published_chronological_age(row.chronological_age)),
        loinc_code=row.loinc_code,
        canonical_name=row.canonical_name,
        raw_name=row.raw_name,
        value=float(row.value),
        unit=row.unit,
        mapping_status=row.mapping_status,
    )


def _dataset_response(page: PublicDatasetPage) -> DatasetResponse:
    """Build the dataset payload and refuse it if a sensitive key appears."""
    response = DatasetResponse(
        rows=[_marker_view(row) for row in page.rows],
        total=page.total,
        limit=page.limit,
        offset=page.offset,
    )
    _guard(response)
    return response


def _timeseries_response(series: PublicTimeseries) -> TimeseriesResponse:
    """Build the timeseries payload and refuse it if a sensitive key appears."""
    response = TimeseriesResponse(
        public_id=series.public_id,
        points=[
            TimeseriesPointView(
                collected_at=point.collected_at,
                chronological_age=_number(published_chronological_age(point.chronological_age)),
                markers=[
                    TimeseriesMarkerView(
                        loinc_code=marker.loinc_code,
                        canonical_name=marker.canonical_name,
                        raw_name=marker.raw_name,
                        value=float(marker.value),
                        unit=marker.unit,
                        mapping_status=marker.mapping_status,
                    )
                    for marker in point.markers
                ],
            )
            for point in series.points
        ],
    )
    _guard(response)
    return response


def _guard(response: DatasetResponse | TimeseriesResponse) -> None:
    """Run the output PII check on the exact JSON the client will receive."""
    try:
        reject_sensitive_output(response.model_dump(mode="json"))
    except PIIValidationError as exc:
        logger.error("public_payload_rejected")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Public response blocked",
        ) from exc


async def enforce_public_rate_limit(
    request: Request,
    response: Response,
    limiter: Annotated[SlidingWindowRateLimiter, Depends(get_public_rate_limiter)],
) -> None:
    """Limit public reads by client IP. The bucket is not shared with account routes."""
    settings = get_settings()
    real_ip = request.headers.get("x-real-ip")
    client_host = request.client.host if request.client is not None else None
    key = resolve_client_key(
        real_ip=real_ip,
        client_host=client_host,
        trust_proxy=settings.trust_proxy_headers,
    )
    decision = await limiter.hit(key)
    response.headers["X-RateLimit-Limit"] = str(decision.limit)
    response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
    if not decision.allowed:
        logger.info("public_dataset_rate_limited")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={
                "Retry-After": str(decision.retry_after_seconds),
                "X-RateLimit-Limit": str(decision.limit),
                "X-RateLimit-Remaining": "0",
            },
        )


@router.get(
    "/dataset",
    response_model=DatasetResponse,
    summary="List anonymized public biomarker rows",
    responses={status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-IP rate limit exceeded"}},
)
async def read_dataset(
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
    _: Annotated[None, Depends(enforce_public_rate_limit)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> DatasetResponse:
    """Return confirmed biomarker rows for profiles that opted in.

    Opt-out profiles are omitted. The body has no name, date of birth, patient
    number, internal UUID, seed hash, or original-document hash.
    """
    page = await dataset_service.read_dataset(limit=limit, offset=offset)
    return _dataset_response(page)


@router.get(
    "/profiles/{public_id}/timeseries",
    response_model=TimeseriesResponse,
    summary="Biomarker time series for one public profile",
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Profile is missing or not public"},
        status.HTTP_429_TOO_MANY_REQUESTS: {"description": "Per-IP rate limit exceeded"},
    },
)
async def read_timeseries(
    dataset_service: Annotated[DatasetService, Depends(get_dataset_service)],
    _: Annotated[None, Depends(enforce_public_rate_limit)],
    public_id: Annotated[str, Path(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9]+$")],
) -> TimeseriesResponse:
    """Return confirmed biomarkers for one opted-in profile.

    A private profile and an unknown id both answer 404, so the response does
    not reveal which accounts exist.
    """
    try:
        series = await dataset_service.read_timeseries(public_id)
    except ProfileNotPublicError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        ) from exc
    return _timeseries_response(series)
