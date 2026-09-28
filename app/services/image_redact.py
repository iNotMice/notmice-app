"""Paint personal lines on a lab photo before any external model sees it.

The reader is local. Tesseract (``eng+rus``) is the engine in this tree until
a later check on real blanks replaces it. The log of a redaction is only a
region count, written by the caller, never the words that were painted.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Protocol

import pytesseract
from PIL import Image, ImageDraw, UnidentifiedImageError

from app.domain.uploads import RedactionEngineUnavailableError, UnreadableImageError
from app.services.pdf_text import line_is_page_chrome

_CONFIDENT_LINE = 0.6
_PAD_PX = 12
_PAINT_PASSES = 2


@dataclass(frozen=True, slots=True)
class OcrWord:
    """One word box. ``confidence`` is 0-1."""

    text: str
    confidence: float
    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True, slots=True)
class RedactedImage:
    """Painted image held in RAM. This is the only frame a model may receive."""

    payload: bytes
    mime_type: str
    region_count: int
    needs_confirmation: bool


@dataclass(frozen=True, slots=True)
class _Line:
    """Words on one horizontal band."""

    text: str
    confidence: float
    left: int
    top: int
    right: int
    bottom: int


class PageReader(Protocol):
    """Local OCR. Implementations must not send pixels to an external API."""

    def read(self, image: Image.Image) -> tuple[OcrWord, ...]:
        """Return word boxes for ``image``."""


class LabImageRedactor(Protocol):
    """Paint personal lines on an in-memory image."""

    def redact(self, payload: bytes, mime_type: str) -> RedactedImage:
        """Return a painted frame. The original ``payload`` is not retained."""


class PassthroughImageRedactor:
    """Test double. Leaves bytes unchanged and treats the frame as certain."""

    def redact(self, payload: bytes, mime_type: str) -> RedactedImage:
        """Return ``payload`` with no painted regions."""
        return RedactedImage(
            payload=payload,
            mime_type=mime_type,
            region_count=0,
            needs_confirmation=False,
        )


class TesseractPageReader:
    """Word boxes from the local Tesseract binary. No network call."""

    def read(self, image: Image.Image) -> tuple[OcrWord, ...]:
        """Read ``image`` with ``eng+rus``.

        Args:
            image: Decoded page. Not written to disk.

        Raises:
            RedactionEngineUnavailableError: The binary or language data is missing.
        """
        try:
            raw = pytesseract.image_to_data(
                image,
                lang="eng+rus",
                config="--psm 6",
                output_type=pytesseract.Output.DICT,
            )
        except pytesseract.TesseractNotFoundError as exc:
            raise RedactionEngineUnavailableError from exc
        except pytesseract.TesseractError as exc:
            raise RedactionEngineUnavailableError from exc
        words: list[OcrWord] = []
        texts = raw["text"]
        for index, text in enumerate(texts):
            cleaned = str(text).strip()
            if not cleaned:
                continue
            confidence = float(raw["conf"][index])
            if confidence < 0:
                continue
            words.append(
                OcrWord(
                    text=cleaned,
                    confidence=confidence / 100,
                    left=int(raw["left"][index]),
                    top=int(raw["top"][index]),
                    width=int(raw["width"][index]),
                    height=int(raw["height"][index]),
                )
            )
        return tuple(words)


class TesseractImageRedactor:
    """Decode an image, paint personal lines, and return a PNG."""

    def __init__(self, reader: PageReader | None = None) -> None:
        self._reader = reader if reader is not None else TesseractPageReader()

    def redact(self, payload: bytes, mime_type: str) -> RedactedImage:
        """Paint personal lines. A low-confidence read is not a refusal.

        Args:
            payload: Complete image bytes.
            mime_type: Sniffed type. The painted frame is always ``image/png``.

        Raises:
            UnreadableImageError: Pillow could not decode ``payload``.
            RedactionEngineUnavailableError: Local OCR could not run.
        """
        del mime_type
        try:
            with Image.open(BytesIO(payload)) as image:
                image.load()
                working = image.convert("RGB")
                painted, region_count, uncertain = redact_lab_image(working, self._reader)
                png = _png_bytes(painted)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise UnreadableImageError from exc
        return RedactedImage(
            payload=png,
            mime_type="image/png",
            region_count=region_count,
            needs_confirmation=uncertain,
        )


def redact_lab_image(
    image: Image.Image,
    reader: PageReader,
) -> tuple[Image.Image, int, bool]:
    """Paint page-chrome lines and say whether a person must confirm the frame.

    No words at all is uncertain: the upload is not refused. A measured row
    and a results heading are left visible.

    Args:
        image: Decoded page.
        reader: Local word locator. Called again after each paint pass.

    Returns:
        Painted RGB image, how many line boxes were filled, and whether the
        read was too weak to send without a person looking at the frame.
    """
    working = image.convert("RGB")
    lines = _lines_from_words(reader.read(working))
    if not lines:
        return working, 0, True
    region_count = 0
    uncertain = False
    for _pass in range(_PAINT_PASSES):
        personal = [line for line in lines if line_is_page_chrome(line.text)]
        if any(line.confidence < _CONFIDENT_LINE for line in personal):
            uncertain = True
        if not personal:
            return working, region_count, uncertain
        _paint(working, personal)
        region_count += len(personal)
        lines = _lines_from_words(reader.read(working))
    if any(line_is_page_chrome(line.text) for line in lines):
        uncertain = True
    return working, region_count, uncertain


def _lines_from_words(words: tuple[OcrWord, ...]) -> tuple[_Line, ...]:
    """Group word boxes into horizontal lines."""
    ordered = sorted(
        (word for word in words if word.text.strip() and word.width > 0 and word.height > 0),
        key=lambda word: (word.top, word.left),
    )
    groups: list[list[OcrWord]] = []
    for word in ordered:
        if not groups:
            groups.append([word])
            continue
        current = groups[-1]
        band_top = min(item.top for item in current)
        band_bottom = max(item.top + item.height for item in current)
        center = word.top + (word.height / 2)
        if band_top <= center <= band_bottom:
            current.append(word)
        else:
            groups.append([word])
    lines: list[_Line] = []
    for group in groups:
        ordered_group = sorted(group, key=lambda item: item.left)
        lines.append(
            _Line(
                text=" ".join(item.text.strip() for item in ordered_group),
                confidence=min(item.confidence for item in ordered_group),
                left=min(item.left for item in ordered_group),
                top=min(item.top for item in ordered_group),
                right=max(item.left + item.width for item in ordered_group),
                bottom=max(item.top + item.height for item in ordered_group),
            )
        )
    return tuple(lines)


def _paint(image: Image.Image, lines: list[_Line]) -> None:
    """Black out the full width of each personal line, with vertical padding."""
    draw = ImageDraw.Draw(image)
    width, height = image.size
    for line in lines:
        top = max(0, line.top - _PAD_PX)
        bottom = min(height, line.bottom + _PAD_PX)
        draw.rectangle((0, top, width, bottom), fill=(0, 0, 0))


def _png_bytes(image: Image.Image) -> bytes:
    """Encode ``image`` as PNG in memory."""
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
