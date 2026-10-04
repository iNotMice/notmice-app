"""Protocol journal HTTP surface. Rows are visible only to their owner."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.accounts import get_current_user, get_current_user_with_current_health_consent
from app.core.deps import get_protocol_service
from app.domain.accounts import UserRecord
from app.domain.protocol import ProtocolEntry, ProtocolEntryNotFoundError, ProtocolValidationError
from app.domain.schemas import ProtocolEntryInput, ProtocolEntryView, ProtocolListResponse
from app.services.protocol import ProtocolService

router = APIRouter(prefix="/api/v1/protocol", tags=["protocol"])


def _view(entry: ProtocolEntry) -> ProtocolEntryView:
    """Map a domain row to the owner payload. The participant id is not included."""
    return ProtocolEntryView(
        id=entry.id,
        kind=entry.kind,
        title=entry.title,
        dose=entry.dose,
        started_on=entry.started_on,
        ended_on=entry.ended_on,
        note=entry.note,
    )


def _http_for(exc: ProtocolValidationError | ProtocolEntryNotFoundError) -> HTTPException:
    """Map a journal error to HTTP. A foreign id uses the same 404 as a missing one."""
    if isinstance(exc, ProtocolEntryNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    return HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("", response_model=ProtocolListResponse)
async def list_entries(
    current: Annotated[UserRecord, Depends(get_current_user)],
    protocol_service: Annotated[ProtocolService, Depends(get_protocol_service)],
) -> ProtocolListResponse:
    """Return journal rows stored for this account."""
    entries = await protocol_service.list_entries(current.id)
    return ProtocolListResponse(entries=[_view(entry) for entry in entries])


@router.post("", response_model=ProtocolEntryView, status_code=status.HTTP_201_CREATED)
async def create_entry(
    payload: ProtocolEntryInput,
    current: Annotated[UserRecord, Depends(get_current_user_with_current_health_consent)],
    protocol_service: Annotated[ProtocolService, Depends(get_protocol_service)],
) -> ProtocolEntryView:
    """Store one journal row on this account."""
    try:
        saved = await protocol_service.create_entry(
            current.id,
            kind=payload.kind,
            title=payload.title,
            dose=payload.dose,
            started_on=payload.started_on,
            ended_on=payload.ended_on,
            note=payload.note,
        )
    except ProtocolValidationError as exc:
        raise _http_for(exc) from exc
    return _view(saved)


@router.patch("/{entry_id}", response_model=ProtocolEntryView)
async def replace_entry(
    entry_id: UUID,
    payload: ProtocolEntryInput,
    current: Annotated[UserRecord, Depends(get_current_user_with_current_health_consent)],
    protocol_service: Annotated[ProtocolService, Depends(get_protocol_service)],
) -> ProtocolEntryView:
    """Replace one journal row. Another account's id answers as not found."""
    try:
        saved = await protocol_service.replace_entry(
            current.id,
            entry_id,
            kind=payload.kind,
            title=payload.title,
            dose=payload.dose,
            started_on=payload.started_on,
            ended_on=payload.ended_on,
            note=payload.note,
        )
    except (ProtocolValidationError, ProtocolEntryNotFoundError) as exc:
        raise _http_for(exc) from exc
    return _view(saved)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: UUID,
    current: Annotated[UserRecord, Depends(get_current_user)],
    protocol_service: Annotated[ProtocolService, Depends(get_protocol_service)],
) -> Response:
    """Delete one journal row. Another account's id answers as not found."""
    try:
        await protocol_service.delete_entry(current.id, entry_id)
    except ProtocolEntryNotFoundError as exc:
        raise _http_for(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
