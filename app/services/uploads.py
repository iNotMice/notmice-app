"""Extract and confirm use-cases. File bytes stay in RAM and are dropped after extract."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

import structlog

from app.domain.enums import MappingStatus
from app.domain.loinc import LoincDictionary
from app.domain.pii import PIIValidationError, contains_personal_text, reject_pii
from app.domain.uploads import (
    CompletedExtract,
    ConfirmedLabResult,
    EmptyPayloadError,
    ExtractedPanel,
    MappedMarker,
    NoMarkersError,
    OwnedLabPanel,
    PayloadTooLargeError,
    RawMarker,
    VisionExtractionError,
    VisionNotConfiguredError,
    VisionTimeoutError,
    map_marker,
    parse_collected_at,
    parser_version_for,
    usable_chronological_age,
)
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.gemini_budget import GeminiTokenBudget
from app.services.image_redact import LabImageRedactor, TesseractImageRedactor
from app.services.loinc_dictionary import load_loinc_dictionary
from app.services.media import sha256_hex, sniff_mime_type
from app.services.pdf_text import prepare_selectable_pdf
from app.services.redaction_holds import RedactionHoldStore
from app.services.vision import ExtractionProvider

logger = structlog.get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RedactionPreview:
    """Painted frame the person must accept before a model call.

    ``preview_png`` is the painted image, not the upload. ``document_sha256``
    is the hash of the original upload.
    """

    token: str
    document_sha256: str
    region_count: int
    preview_png: bytes


class LabResultStore(Protocol):
    """Persistence contract used by UploadService.confirm."""

    async def save_confirmed(
        self,
        *,
        user_id: UUID,
        collected_at: date | None,
        lab_name: str | None,
        chronological_age: Decimal | None,
        parser_version: str,
        confirmed_at: datetime,
        document_sha256: str,
        markers: tuple[MappedMarker, ...],
    ) -> ConfirmedLabResult:
        """Insert confirmed rows and provenance."""

    async def list_confirmed(self, user_id: UUID) -> tuple[OwnedLabPanel, ...]:
        """Return confirmed panels for ``user_id``, oldest first."""

    async def delete_confirmed(self, user_id: UUID) -> int:
        """Delete confirmed panels owned by ``user_id``. The account itself stays."""


class UploadService:
    """In-memory extract plus confirmed persistence."""

    def __init__(
        self,
        *,
        vision: ExtractionProvider,
        sessions: InMemoryExtractSessionStore,
        lab_results: LabResultStore,
        max_upload_bytes: int,
        budget: GeminiTokenBudget,
        dictionary: LoincDictionary | None = None,
        image_redactor: LabImageRedactor | None = None,
        redaction_holds: RedactionHoldStore | None = None,
    ) -> None:
        self._vision = vision
        self._sessions = sessions
        self._lab_results = lab_results
        self._max_upload_bytes = max_upload_bytes
        self._budget = budget
        self._dictionary = dictionary if dictionary is not None else load_loinc_dictionary()
        self._images = image_redactor if image_redactor is not None else TesseractImageRedactor()
        self._holds = (
            redaction_holds
            if redaction_holds is not None
            else RedactionHoldStore(ttl_seconds=1_800)
        )

    async def extract(
        self,
        user_id: UUID,
        payload: bytes,
        *,
        client_key: str,
    ) -> CompletedExtract | RedactionPreview:
        """Hash, parse, and forget the original bytes.

        A photo is painted locally before any model call. When that paint is
        uncertain, the return value is the painted frame and the model is not
        called.

        Args:
            user_id: Authenticated owner.
            payload: Complete file in RAM.
            client_key: Address that owns the IP token bucket.

        Returns:
            Extract session whose panel does not include file bytes, or a
            painted preview that still needs a person.

        Raises:
            GeminiBudgetExhaustedError: The daily budget cannot cover another Gemini call.
        """
        if not payload:
            raise EmptyPayloadError
        if len(payload) > self._max_upload_bytes:
            raise PayloadTooLargeError
        mime_type = sniff_mime_type(payload)
        digest = sha256_hex(payload)
        try:
            if mime_type == "application/pdf":
                prepared = await asyncio.to_thread(prepare_selectable_pdf, payload)
                if prepared is not None:
                    if not prepared.model_text.strip():
                        raise NoMarkersError
                    logger.info(
                        "pdf_page_redacted",
                        page_count=prepared.page_count,
                        dropped_lines=prepared.dropped_lines,
                    )
                    return await self._run_model(
                        user_id,
                        client_key=client_key,
                        document_sha256=digest,
                        mime_type=mime_type,
                        text=prepared.model_text,
                        media=None,
                        media_mime=None,
                    )
                return await self._run_model(
                    user_id,
                    client_key=client_key,
                    document_sha256=digest,
                    mime_type=mime_type,
                    text=None,
                    media=payload,
                    media_mime=mime_type,
                )
            redacted = await asyncio.to_thread(self._images.redact, payload, mime_type)
            logger.info(
                "image_redacted",
                region_count=redacted.region_count,
                needs_confirmation=redacted.needs_confirmation,
            )
            if redacted.needs_confirmation:
                token = self._holds.put(
                    user_id,
                    document_sha256=digest,
                    payload=redacted.payload,
                    mime_type=redacted.mime_type,
                )
                return RedactionPreview(
                    token=token,
                    document_sha256=digest,
                    region_count=redacted.region_count,
                    preview_png=redacted.payload,
                )
            return await self._run_model(
                user_id,
                client_key=client_key,
                document_sha256=digest,
                mime_type=mime_type,
                text=None,
                media=redacted.payload,
                media_mime=redacted.mime_type,
            )
        finally:
            del payload

    async def confirm_redaction(
        self,
        user_id: UUID,
        token: str,
        *,
        client_key: str,
    ) -> CompletedExtract:
        """Send the already painted frame to the model and drop it.

        Args:
            user_id: Authenticated owner.
            token: Token from the redaction preview.
            client_key: Address that owns the IP token bucket.
        """
        hold = self._holds.pop(token, user_id)
        try:
            return await self._run_model(
                user_id,
                client_key=client_key,
                document_sha256=hold.document_sha256,
                mime_type=hold.mime_type,
                text=None,
                media=hold.payload,
                media_mime=hold.mime_type,
            )
        finally:
            del hold

    def discard_redaction(self, user_id: UUID, token: str) -> None:
        """Drop a painted frame without calling the model.

        Args:
            user_id: Authenticated owner.
            token: Token from the redaction preview.
        """
        self._holds.pop(token, user_id)
        logger.info("image_redaction_discarded")

    async def _run_model(
        self,
        user_id: UUID,
        *,
        client_key: str,
        document_sha256: str,
        mime_type: str,
        text: str | None,
        media: bytes | None,
        media_mime: str | None,
    ) -> CompletedExtract:
        """Call the model, map markers, and store an extract session."""
        hold = self._budget.reserve(user_id, client_key)
        try:
            if text is not None:
                parsed = await self._vision.extract_from_text(text)
            else:
                if media is None or media_mime is None:
                    raise NoMarkersError
                parsed = await self._vision.extract_from_media(media, media_mime)
        except (VisionNotConfiguredError, VisionTimeoutError):
            self._budget.release(hold)
            raise
        except VisionExtractionError as exc:
            self._budget.commit(hold, exc.tokens_used)
            raise
        else:
            usage = self._budget.commit(hold, parsed.tokens_used)
        raw = parsed.extraction
        mapped = tuple(map_marker(item, self._dictionary) for item in raw.markers)
        if not mapped:
            raise NoMarkersError
        chronological_age = usable_chronological_age(raw.chronological_age)
        panel = ExtractedPanel(
            document_sha256=document_sha256,
            parser_version=parser_version_for(
                self._vision.name,
                self._vision.model_id,
                dictionary_version=self._dictionary.version,
            ),
            lab_name=raw.lab_name,
            collected_at=parse_collected_at(raw.collected_at),
            chronological_age=chronological_age,
            markers=mapped,
        )
        session = self._sessions.put(user_id, panel)
        logger.info(
            "lab_extracted",
            marker_count=len(mapped),
            unmapped_count=sum(
                1 for marker in mapped if marker.mapping_status is MappingStatus.UNMAPPED
            ),
            mime_type=mime_type,
            parser_version=panel.parser_version,
        )
        return CompletedExtract(
            session=session,
            tokens_used=usage.tokens_used,
            tokens_limit=usage.tokens_limit,
            warning=usage.warning,
        )

    async def confirm(
        self,
        user_id: UUID,
        extract_token: str,
        *,
        lab_name: str | None,
        collected_at: date | None,
        chronological_age: Decimal | None,
        markers: tuple[RawMarker, ...],
    ) -> ConfirmedLabResult:
        """Persist edited values and drop the extract session.

        SHA-256 and parser_version always come from the session, never the client.

        Args:
            user_id: Authenticated owner.
            extract_token: Token from extract.
            lab_name: Optional override from review UI.
            collected_at: Optional override from review UI.
            chronological_age: Optional override from review UI.
            markers: Human-edited analyte rows.
        """
        session = self._sessions.pop(extract_token, user_id)
        mapped = tuple(
            _marker_without_personal_text(map_marker(item, self._dictionary)) for item in markers
        )
        if not mapped:
            raise NoMarkersError
        stored_lab_name = _label_without_personal_text(
            lab_name if lab_name is not None else session.panel.lab_name
        )
        stored_age = usable_chronological_age(
            chronological_age if chronological_age is not None else session.panel.chronological_age
        )
        reject_pii(
            {
                "lab_name": stored_lab_name,
                "markers": [
                    {"raw_name": marker.raw_name, "unit": marker.unit} for marker in mapped
                ],
            }
        )
        confirmed_at = datetime.now(UTC)
        result = await self._lab_results.save_confirmed(
            user_id=user_id,
            collected_at=collected_at if collected_at is not None else session.panel.collected_at,
            lab_name=stored_lab_name,
            chronological_age=stored_age,
            parser_version=session.panel.parser_version,
            confirmed_at=confirmed_at,
            document_sha256=session.panel.document_sha256,
            markers=mapped,
        )
        logger.info(
            "lab_confirmed",
            lab_result_id=str(result.lab_result_id),
            marker_count=result.marker_count,
        )
        return result

    async def list_confirmed(self, user_id: UUID) -> tuple[OwnedLabPanel, ...]:
        """Return panels this account has already confirmed.

        Args:
            user_id: Authenticated owner.
        """
        return await self._lab_results.list_confirmed(user_id)

    async def delete_confirmed(self, user_id: UUID) -> None:
        """Delete this account's confirmed panels. The account and phrase hash stay.

        Args:
            user_id: Authenticated owner.
        """
        removed = await self._lab_results.delete_confirmed(user_id)
        logger.info("lab_results_deleted", removed=removed)


def _label_without_personal_text(value: str | None) -> str | None:
    """Drop a laboratory name that contains a phone number or a person's name."""
    if value is None:
        return None
    if contains_personal_text(value, parent_key="lab_name"):
        return None
    return value


def _marker_without_personal_text(marker: MappedMarker) -> MappedMarker:
    """Keep the measured value and drop a label that contains personal text.

    Mapping runs before this, so a Russian analyte that the dictionary knows
    keeps its canonical id even when the printed name looks like a person.
    """
    raw_name = marker.raw_name
    unit = marker.unit
    if not _marker_text_is_personal(raw_name, unit):
        return marker
    raw_name = marker.canonical_id or "Unmapped analyte"
    if _marker_text_is_personal(raw_name, unit):
        unit = "1"
    return replace(marker, raw_name=raw_name, unit=unit)


def _marker_text_is_personal(raw_name: str, unit: str) -> bool:
    """Return True when the analyte label or unit would be rejected as personal data."""
    try:
        reject_pii({"raw_name": raw_name, "unit": unit})
    except PIIValidationError:
        return True
    return False
