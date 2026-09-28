"""Rasterize an image-only lab PDF and paint each page before any model sees it.

Selectable text reports never reach this module. A scan has no text layer, so
the original file would otherwise be sent whole. Pages are rendered in memory,
personal lines are painted with the same local reader as a photo, and only
those painted pages may leave the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

import pypdfium2 as pdfium
from PIL import Image

from app.domain.uploads import PayloadTooLargeError, UnreadableImageError
from app.services.image_redact import PageReader, TesseractPageReader, redact_lab_image

_MAX_PAGES = 12
_RENDER_SCALE = 2.0
_MAX_EDGE = 2400


@dataclass(frozen=True, slots=True)
class RedactedScan:
    """Painted pages held in RAM. ``payload`` is the only file a model may receive.

    A single page is a PNG, and ``preview_png`` is that same PNG. Several pages
    are a new PDF of the painted rasters. ``preview_png`` is those pages stacked
    for the person to read. Neither field is the uploaded original.
    """

    payload: bytes
    mime_type: str
    region_count: int
    needs_confirmation: bool
    preview_png: bytes
    page_count: int


class PageRasterizer(Protocol):
    """Render PDF pages to images. Implementations must not write the file."""

    def render(self, payload: bytes) -> tuple[Image.Image, ...]:
        """Return one RGB image per page."""


class LabScanRedactor(Protocol):
    """Paint personal lines on an image-only PDF."""

    def redact(self, payload: bytes) -> RedactedScan:
        """Return painted pages. The original ``payload`` is not retained."""


class PdfiumRasterizer:
    """In-memory page bitmaps from PDFium. No temporary file."""

    def render(self, payload: bytes) -> tuple[Image.Image, ...]:
        """Render up to ``_MAX_PAGES`` pages.

        Args:
            payload: Complete PDF bytes.

        Returns:
            RGB page images, in order.

        Raises:
            UnreadableImageError: The PDF could not be opened or drawn.
            PayloadTooLargeError: The document has more than ``_MAX_PAGES`` pages.
        """
        try:
            document = pdfium.PdfDocument(payload)
        except pdfium.PdfiumError as exc:
            raise UnreadableImageError from exc
        try:
            count = len(document)
            if count < 1:
                raise UnreadableImageError
            if count > _MAX_PAGES:
                raise PayloadTooLargeError
            pages: list[Image.Image] = []
            for index in range(count):
                page = document[index]
                try:
                    bitmap = page.render(scale=_RENDER_SCALE)
                    try:
                        image = bitmap.to_pil().convert("RGB")
                    finally:
                        bitmap.close()
                finally:
                    page.close()
                pages.append(_limit_edge(image))
            return tuple(pages)
        except pdfium.PdfiumError as exc:
            raise UnreadableImageError from exc
        finally:
            document.close()


class PdfiumScanRedactor:
    """Render a scan, paint personal lines on every page, and drop the original."""

    def __init__(
        self,
        reader: PageReader | None = None,
        rasterizer: PageRasterizer | None = None,
    ) -> None:
        self._reader = reader if reader is not None else TesseractPageReader()
        self._rasterizer = rasterizer if rasterizer is not None else PdfiumRasterizer()

    def redact(self, payload: bytes) -> RedactedScan:
        """Paint every page. A weak read asks a person to look, and is not a refusal.

        Args:
            payload: Image-only PDF. Not included in the result.

        Returns:
            Painted pages safe to show and, after confirmation when needed, to send.

        Raises:
            UnreadableImageError: A page could not be rendered.
            PayloadTooLargeError: The document has too many pages.
            RedactionEngineUnavailableError: Local OCR could not run.
        """
        rendered = self._rasterizer.render(payload)
        if not rendered:
            raise UnreadableImageError
        painted: list[Image.Image] = []
        region_count = 0
        uncertain = False
        for page in rendered:
            image, count, page_uncertain = redact_lab_image(page, self._reader)
            painted.append(image)
            region_count += count
            uncertain = uncertain or page_uncertain
        pages = tuple(painted)
        if len(pages) == 1:
            png = _png_bytes(pages[0])
            return RedactedScan(
                payload=png,
                mime_type="image/png",
                region_count=region_count,
                needs_confirmation=uncertain,
                preview_png=png,
                page_count=1,
            )
        return RedactedScan(
            payload=_pdf_bytes(pages),
            mime_type="application/pdf",
            region_count=region_count,
            needs_confirmation=uncertain,
            preview_png=_stack_png(pages),
            page_count=len(pages),
        )


def _limit_edge(image: Image.Image) -> Image.Image:
    """Shrink a page so the longer side is at most ``_MAX_EDGE`` pixels."""
    edge = max(image.size)
    if edge <= _MAX_EDGE:
        return image
    scale = _MAX_EDGE / edge
    size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def _png_bytes(image: Image.Image) -> bytes:
    """Encode ``image`` as PNG in memory."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _pdf_bytes(pages: tuple[Image.Image, ...]) -> bytes:
    """Build a new PDF whose pages are the painted rasters and nothing else."""
    buffer = BytesIO()
    first, *rest = pages
    first.save(buffer, format="PDF", save_all=True, append_images=list(rest))
    return buffer.getvalue()


def _stack_png(pages: tuple[Image.Image, ...]) -> bytes:
    """Stack painted pages into one PNG so a person can read every page."""
    width = max(page.width for page in pages)
    height = sum(page.height for page in pages)
    canvas = Image.new("RGB", (width, height), (255, 255, 255))
    top = 0
    for page in pages:
        canvas.paste(page, (0, top))
        top += page.height
    return _png_bytes(canvas)
