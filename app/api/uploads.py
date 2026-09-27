"""Upload extract/confirm HTTP surface."""

from __future__ import annotations

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse, Response

from app.api.accounts import get_current_user
from app.core.config import get_settings
from app.core.deps import get_upload_service
from app.core.rate_limit import resolve_client_key
from app.domain.accounts import UserRecord
from app.domain.pii import PIIValidationError
from app.domain.schemas import (
    ConfirmRequest,
    ConfirmResponse,
    ExtractedMarkerView,
    ExtractResponse,
    OwnedLabResultsResponse,
    OwnedLabResultView,
    OwnedMarkerView,
)
from app.domain.uploads import (
    EmptyPayloadError,
    ExtractSessionNotFoundError,
    GeminiBudgetExhaustedError,
    NoMarkersError,
    PayloadTooLargeError,
    RawMarker,
    UnsupportedMediaTypeError,
    UploadError,
    VisionExtractionError,
    VisionNotConfiguredError,
    VisionTimeoutError,
    usable_chronological_age,
)
from app.services.uploads import UploadService

router = APIRouter(prefix="/api/v1/uploads", tags=["uploads"])


async def gemini_budget_exhausted_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Return the caller's own counter when a Gemini budget refuses the extract."""
    tokens_used = exc.tokens_used if isinstance(exc, GeminiBudgetExhaustedError) else 0
    tokens_limit = exc.tokens_limit if isinstance(exc, GeminiBudgetExhaustedError) else 1
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Daily extraction limit reached",
            "tokens_used": tokens_used,
            "tokens_limit": tokens_limit,
            "warning": True,
        },
    )


def _http_for(exc: UploadError) -> HTTPException:
    """Map domain errors to HTTP responses without leaking file contents."""
    if isinstance(exc, UnsupportedMediaTypeError):
        return HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Unsupported file type",
        )
    if isinstance(exc, PayloadTooLargeError):
        return HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large",
        )
    if isinstance(exc, EmptyPayloadError):
        return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if isinstance(exc, NoMarkersError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No numeric markers found",
        )
    if isinstance(exc, ExtractSessionNotFoundError):
        return HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Extract session expired",
        )
    if isinstance(exc, VisionNotConfiguredError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vision provider is not configured",
        )
    if isinstance(exc, VisionTimeoutError):
        return HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Extraction timed out",
        )
    if isinstance(exc, VisionExtractionError):
        return HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Extraction failed")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upload request failed")


@router.post("/extract", response_model=ExtractResponse)
async def extract_upload(
    request: Request,
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ExtractResponse:
    """Parse a PDF or image in RAM and return markers for human review."""
    settings = get_settings()
    client_key = resolve_client_key(
        real_ip=request.headers.get("x-real-ip"),
        client_host=request.client.host if request.client is not None else None,
        trust_proxy=settings.trust_proxy_headers,
    )
    payload = await file.read()
    try:
        completed = await upload_service.extract(current.id, payload, client_key=client_key)
    except GeminiBudgetExhaustedError:
        raise
    except UploadError as exc:
        raise _http_for(exc) from exc
    finally:
        del payload
    session = completed.session
    panel = session.panel
    chronological_age = usable_chronological_age(panel.chronological_age)
    chronological_age_value = float(chronological_age) if chronological_age is not None else None
    return ExtractResponse(
        extract_token=session.token,
        document_sha256=panel.document_sha256,
        parser_version=panel.parser_version,
        lab_name=panel.lab_name,
        collected_at=panel.collected_at,
        chronological_age=chronological_age_value,
        markers=[
            ExtractedMarkerView(
                raw_name=marker.raw_name,
                canonical_id=marker.canonical_id,
                loinc_code=marker.loinc_code,
                value=float(marker.value),
                unit=marker.unit,
                confidence=marker.confidence,
                mapping_status=marker.mapping_status.value,
                within_range=marker.within_range,
            )
            for marker in panel.markers
        ],
        tokens_used=completed.tokens_used,
        tokens_limit=completed.tokens_limit,
        warning=completed.warning,
    )


@router.post("/confirm", response_model=ConfirmResponse)
async def confirm_upload(
    payload: ConfirmRequest,
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
) -> ConfirmResponse:
    """Persist reviewed values. SHA-256 comes from the extract session.

    A name or phone in the laboratory label is dropped. The numeric markers are kept.
    """
    try:
        result = await upload_service.confirm(
            current.id,
            payload.extract_token,
            lab_name=payload.lab_name,
            collected_at=payload.collected_at,
            chronological_age=(
                Decimal(str(payload.chronological_age))
                if payload.chronological_age is not None
                else None
            ),
            markers=tuple(
                RawMarker(raw_name=item.raw_name, value=item.value, unit=item.unit)
                for item in payload.markers
            ),
        )
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Forbidden field",
        ) from exc
    except UploadError as exc:
        raise _http_for(exc) from exc
    return ConfirmResponse(
        lab_result_id=result.lab_result_id,
        document_sha256=result.document_sha256,
        parser_version=result.parser_version,
        confirmed_at=result.confirmed_at,
        marker_count=result.marker_count,
    )


@router.delete("/results", status_code=status.HTTP_204_NO_CONTENT)
async def delete_own_results(
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
) -> Response:
    """Delete panels this account confirmed. The account and recovery phrase stay."""
    await upload_service.delete_confirmed(current.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/results", response_model=OwnedLabResultsResponse)
async def list_own_results(
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
) -> OwnedLabResultsResponse:
    """Return panels this account confirmed. Other accounts cannot read them."""
    panels = await upload_service.list_confirmed(current.id)
    return OwnedLabResultsResponse(
        results=[
            OwnedLabResultView(
                collected_at=panel.collected_at,
                lab_name=panel.lab_name,
                chronological_age=(
                    float(panel.chronological_age) if panel.chronological_age is not None else None
                ),
                confirmed_at=panel.confirmed_at,
                document_sha256=panel.document_sha256,
                markers=[
                    OwnedMarkerView(
                        raw_name=marker.raw_name,
                        canonical_id=marker.canonical_id,
                        loinc_code=marker.loinc_code,
                        value=float(marker.value),
                        unit=marker.unit,
                    )
                    for marker in panel.markers
                ],
            )
            for panel in panels
        ]
    )
