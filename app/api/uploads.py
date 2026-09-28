"""Upload extract/confirm HTTP surface."""

from __future__ import annotations

import base64
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
    RedactionConfirmRequest,
    RedactionPreviewResponse,
)
from app.domain.uploads import (
    CompletedExtract,
    EmptyPayloadError,
    ExtractSessionNotFoundError,
    GeminiBudgetExhaustedError,
    NoMarkersError,
    PayloadTooLargeError,
    RawMarker,
    RedactionEngineUnavailableError,
    UnreadableImageError,
    UnsupportedMediaTypeError,
    UploadError,
    VisionExtractionError,
    VisionNotConfiguredError,
    VisionTimeoutError,
    usable_chronological_age,
)
from app.services.uploads import RedactionPreview, UploadService

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


def _float_or_none(value: Decimal | None) -> float | None:
    """Return a JSON number, or None when the blank did not print one."""
    if value is None:
        return None
    return float(value)


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
    if isinstance(exc, UnreadableImageError):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not read image",
        )
    if isinstance(exc, RedactionEngineUnavailableError):
        return HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Local redaction engine is not available",
        )
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


def _extract_response(completed: CompletedExtract) -> ExtractResponse:
    """Map a finished extract to the review payload."""
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
                reported_value=float(marker.reported_value),
                reported_unit=marker.reported_unit,
                reference_low=_float_or_none(marker.reference_low),
                reference_high=_float_or_none(marker.reference_high),
                reference_text=marker.reference_text,
                lab_flag=marker.lab_flag,
            )
            for marker in panel.markers
        ],
        tokens_used=completed.tokens_used,
        tokens_limit=completed.tokens_limit,
        warning=completed.warning,
    )


@router.post(
    "/extract",
    response_model=ExtractResponse,
    responses={202: {"model": RedactionPreviewResponse}},
)
async def extract_upload(
    request: Request,
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
    file: Annotated[UploadFile, File()],
) -> ExtractResponse | JSONResponse:
    """Parse a PDF or image in RAM and return markers for human review.

    A photo or an image-only PDF may instead return 202 with the painted
    pages. The model is not called until that frame is confirmed. The original
    scan is not part of the response.
    """
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
    if isinstance(completed, RedactionPreview):
        body = RedactionPreviewResponse(
            redaction_token=completed.token,
            document_sha256=completed.document_sha256,
            region_count=completed.region_count,
            preview_png=base64.b64encode(completed.preview_png).decode("ascii"),
        )
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=body.model_dump())
    return _extract_response(completed)


def _client_key(request: Request) -> str:
    """Return the address that owns the caller's token bucket."""
    settings = get_settings()
    return resolve_client_key(
        real_ip=request.headers.get("x-real-ip"),
        client_host=request.client.host if request.client is not None else None,
        trust_proxy=settings.trust_proxy_headers,
    )


@router.post("/redaction/confirm", response_model=ExtractResponse)
async def confirm_redaction(
    request: Request,
    payload: RedactionConfirmRequest,
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
) -> ExtractResponse:
    """Extract markers from a painted frame the caller already accepted."""
    try:
        completed = await upload_service.confirm_redaction(
            current.id,
            payload.redaction_token,
            client_key=_client_key(request),
        )
    except GeminiBudgetExhaustedError:
        raise
    except UploadError as exc:
        raise _http_for(exc) from exc
    return _extract_response(completed)


@router.post("/redaction/discard", status_code=status.HTTP_204_NO_CONTENT)
async def discard_redaction(
    payload: RedactionConfirmRequest,
    current: Annotated[UserRecord, Depends(get_current_user)],
    upload_service: Annotated[UploadService, Depends(get_upload_service)],
) -> Response:
    """Drop a painted frame. The model is not called."""
    try:
        upload_service.discard_redaction(current.id, payload.redaction_token)
    except UploadError as exc:
        raise _http_for(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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
                RawMarker(
                    raw_name=item.raw_name,
                    value=item.value,
                    unit=item.unit,
                    reported_value=item.reported_value,
                    reported_unit=item.reported_unit,
                    reference_low=item.reference_low,
                    reference_high=item.reference_high,
                    reference_text=item.reference_text,
                    lab_flag=item.lab_flag,
                )
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
                        reported_value=_float_or_none(marker.reported_value),
                        reported_unit=marker.reported_unit,
                        reference_low=_float_or_none(marker.reference_low),
                        reference_high=_float_or_none(marker.reference_high),
                        reference_text=marker.reference_text,
                        lab_flag=marker.lab_flag,
                    )
                    for marker in panel.markers
                ],
            )
            for panel in panels
        ]
    )
