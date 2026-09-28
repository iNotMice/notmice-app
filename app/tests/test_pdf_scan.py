"""Image-only PDFs are painted locally. The original file never reaches the model."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image, ImageDraw, ImageFont
from structlog.testing import capture_logs

from app.domain.accounts import UserRecord
from app.domain.uploads import (
    ExtractSessionNotFoundError,
    PayloadTooLargeError,
    UnreadableImageError,
)
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.image_redact import OcrWord, PassthroughImageRedactor
from app.services.pdf_scan import PdfiumRasterizer, PdfiumScanRedactor, RedactedScan
from app.services.uploads import RedactionPreview, UploadService
from app.services.vision import ProviderExtraction
from app.tests.test_uploads import FakeVision, InMemoryLabStore, _budget, _done, _text_pdf

_NAME = "Anna Synthetic"
_BIRTH = "1990-01-01"


class RememberingVision(FakeVision):
    """Keeps the media bytes so a test can check what the model would receive."""

    def __init__(self) -> None:
        super().__init__()
        self.last_media: bytes | None = None

    async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
        self.last_media = payload
        return await super().extract_from_media(payload, mime_type)


class AlternatingReader:
    """Header words on odd reads, table words on even reads. Ignores the pixels."""

    def __init__(self, header: tuple[OcrWord, ...], table: tuple[OcrWord, ...]) -> None:
        self._header = header
        self._table = table
        self.calls = 0

    def read(self, image: Image.Image) -> tuple[OcrWord, ...]:
        del image
        self.calls += 1
        if self.calls % 2 == 1:
            return self._header
        return self._table


class FixedRasterizer:
    """Returns prepared pages and records the PDF it was given."""

    def __init__(self, pages: tuple[Image.Image, ...]) -> None:
        self._pages = pages
        self.seen: list[bytes] = []

    def render(self, payload: bytes) -> tuple[Image.Image, ...]:
        self.seen.append(payload)
        return tuple(page.copy() for page in self._pages)


class EmptyReader:
    """No words. The scan must still not fall through to the original file."""

    def read(self, image: Image.Image) -> tuple[OcrWord, ...]:
        del image
        return ()


class ExplodingScan:
    """Fails the test when a selectable PDF is rasterized."""

    def redact(self, payload: bytes) -> RedactedScan:
        del payload
        raise AssertionError("selectable PDF must stay on the text path")


def _user() -> UserRecord:
    return UserRecord(id=uuid4(), public_id="nmtest", is_public=False, created_at=datetime.now(UTC))


def _service(vision: FakeVision, scan: PdfiumScanRedactor | ExplodingScan) -> UploadService:
    return UploadService(
        vision=vision,
        sessions=InMemoryExtractSessionStore(ttl_seconds=60),
        lab_results=InMemoryLabStore(),
        max_upload_bytes=4_000_000,
        budget=_budget(),
        image_redactor=PassthroughImageRedactor(),
        scan_redactor=scan,
    )


def _word(text: str, *, left: int, top: int, confidence: float) -> OcrWord:
    return OcrWord(text=text, confidence=confidence, left=left, top=top, width=80, height=28)


def _header_words(confidence: float) -> tuple[OcrWord, ...]:
    return (
        _word("Patient:", left=10, top=16, confidence=confidence),
        _word("Anna", left=100, top=16, confidence=confidence),
        _word("Synthetic", left=190, top=16, confidence=confidence),
        _word("Albumin", left=10, top=140, confidence=0.95),
        _word("4.5", left=110, top=140, confidence=0.95),
        _word("g/dL", left=200, top=140, confidence=0.95),
    )


def _table_words() -> tuple[OcrWord, ...]:
    return (
        _word("Albumin", left=10, top=140, confidence=0.95),
        _word("4.5", left=110, top=140, confidence=0.95),
        _word("g/dL", left=200, top=140, confidence=0.95),
    )


def _image_pdf(pages: list[Image.Image]) -> bytes:
    """Wrap rasters in a PDF that has no selectable text."""
    buffer = BytesIO()
    first, *rest = (page.convert("RGB") for page in pages)
    first.save(buffer, format="PDF", save_all=True, append_images=rest)
    return buffer.getvalue()


def _blank(width: int = 400, height: int = 220) -> Image.Image:
    return Image.new("RGB", (width, height), (255, 255, 255))


@pytest.mark.asyncio
async def test_text_pdf_is_not_rasterized() -> None:
    """A report with a text layer still sends redacted text, not page images."""
    vision = RememberingVision()
    service = _service(vision, ExplodingScan())
    payload = _text_pdf(
        "Serum Albumin 46.2 g/L  Creatinine 0.88 mg/dL  Glucose 84 mg/dL extra padding text"
    )
    completed = _done(await service.extract(_user().id, payload, client_key="203.0.113.10"))
    assert vision.text_calls == 1
    assert vision.media_calls == 0
    assert completed.session.panel.markers


@pytest.mark.asyncio
async def test_confident_scan_sends_painted_png_not_the_pdf() -> None:
    """One painted page is the model payload. The uploaded PDF is not inside it."""
    original = _image_pdf([_blank()])
    rasterizer = FixedRasterizer((_blank(),))
    reader = AlternatingReader(_header_words(0.95), _table_words())
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(reader, rasterizer))
    with capture_logs() as logs:
        completed = _done(await service.extract(_user().id, original, client_key="203.0.113.10"))
    assert rasterizer.seen == [original]
    assert vision.media_calls == 1
    assert vision.text_calls == 0
    assert vision.last_media_mime == "image/png"
    assert vision.last_media is not None
    assert vision.last_media != original
    assert original not in vision.last_media
    painted = Image.open(BytesIO(vision.last_media))
    assert painted.getpixel((40, 28)) == (0, 0, 0)
    assert completed.session.panel.document_sha256
    assert all("Anna" not in str(event.values()) for event in logs)
    assert any(
        event.get("event") == "scan_pdf_redacted"
        and event.get("region_count") == 1
        and event.get("page_count") == 1
        for event in logs
    )


@pytest.mark.asyncio
async def test_uncertain_scan_waits_and_confirm_sends_the_painted_page() -> None:
    """A weak read holds the painted page. Confirm is the first model call."""
    original = _image_pdf([_blank()])
    reader = AlternatingReader(_header_words(0.2), _table_words())
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(reader, FixedRasterizer((_blank(),))))
    user = _user()
    preview = await service.extract(user.id, original, client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    assert preview.region_count == 1
    assert vision.media_calls == 0
    painted = Image.open(BytesIO(preview.preview_png))
    assert painted.getpixel((40, 28)) == (0, 0, 0)
    await service.confirm_redaction(user.id, preview.token, client_key="203.0.113.10")
    assert vision.media_calls == 1
    assert vision.last_media == preview.preview_png
    assert vision.last_media != original
    assert original not in (vision.last_media or b"")


@pytest.mark.asyncio
async def test_two_page_scan_sends_a_new_pdf_of_painted_pages() -> None:
    """Each page is painted. The model receives a new PDF, not the upload."""
    original = _image_pdf([_blank(), _blank()])
    pages = (_blank(), _blank())
    reader = AlternatingReader(_header_words(0.95), _table_words())
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(reader, FixedRasterizer(pages)))
    completed = _done(await service.extract(_user().id, original, client_key="203.0.113.10"))
    assert vision.last_media_mime == "application/pdf"
    assert vision.last_media is not None
    assert vision.last_media.startswith(b"%PDF")
    assert vision.last_media != original
    assert original not in vision.last_media
    assert completed.session.panel.document_sha256
    preview_pages = PdfiumRasterizer().render(vision.last_media)
    assert len(preview_pages) == 2
    assert preview_pages[0].getpixel((40, 28)) == (0, 0, 0)
    assert preview_pages[1].getpixel((40, 28)) == (0, 0, 0)


@pytest.mark.asyncio
async def test_discard_drops_a_scan_without_a_model_call() -> None:
    """Cancel frees the painted pages. A later confirm does not extract them."""
    original = _image_pdf([_blank()])
    reader = AlternatingReader(_header_words(0.2), _table_words())
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(reader, FixedRasterizer((_blank(),))))
    user = _user()
    preview = await service.extract(user.id, original, client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    service.discard_redaction(user.id, preview.token)
    assert vision.media_calls == 0
    with pytest.raises(ExtractSessionNotFoundError):
        await service.confirm_redaction(user.id, preview.token, client_key="203.0.113.10")


@pytest.mark.asyncio
async def test_unreadable_scan_is_not_sent_whole() -> None:
    """No local words is a confirmation, not a reason to upload the original PDF."""
    original = _image_pdf([_blank()])
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(EmptyReader(), FixedRasterizer((_blank(),))))
    user = _user()
    preview = await service.extract(user.id, original, client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    assert preview.region_count == 0
    assert vision.media_calls == 0
    await service.confirm_redaction(user.id, preview.token, client_key="203.0.113.10")
    assert vision.last_media == preview.preview_png
    assert vision.last_media != original
    assert original not in (vision.last_media or b"")


@pytest.mark.asyncio
async def test_uncertain_two_page_confirm_sends_the_painted_pdf() -> None:
    """The held file is the new PDF of painted pages, not the preview stack."""
    original = _image_pdf([_blank(), _blank()])
    reader = AlternatingReader(_header_words(0.2), _table_words())
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor(reader, FixedRasterizer((_blank(), _blank()))))
    user = _user()
    preview = await service.extract(user.id, original, client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    assert preview.preview_png.startswith(b"\x89PNG")
    await service.confirm_redaction(user.id, preview.token, client_key="203.0.113.10")
    assert vision.last_media is not None
    assert vision.last_media.startswith(b"%PDF")
    assert vision.last_media != preview.preview_png
    assert vision.last_media != original
    assert original not in vision.last_media


def test_too_many_pages_is_refused_before_ocr() -> None:
    """A long scan is not painted and is not a reason to send the original."""
    payload = _image_pdf([Image.new("RGB", (20, 20), (255, 255, 255)) for _ in range(13)])
    with pytest.raises(PayloadTooLargeError):
        PdfiumScanRedactor().redact(payload)


def test_corrupt_pdf_is_unreadable() -> None:
    """PDFium's load error becomes the upload error, not a pass-through."""
    with pytest.raises(UnreadableImageError):
        PdfiumRasterizer().render(b"%PDF-1.4\nbogus")


@pytest.mark.asyncio
async def test_long_scan_does_not_call_the_model() -> None:
    """The service stops on the page cap with no Vision call."""
    payload = _image_pdf([Image.new("RGB", (20, 20), (255, 255, 255)) for _ in range(13)])
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor())
    with pytest.raises(PayloadTooLargeError):
        await service.extract(_user().id, payload, client_key="203.0.113.10")
    assert vision.media_calls == 0
    assert vision.text_calls == 0


def _font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ):
        if os.path.isfile(path):
            return ImageFont.truetype(path, size)
    pytest.skip("No TrueType font for the lab fixture")
    raise AssertionError


def _lab_page() -> Image.Image:
    image = Image.new("RGB", (1400, 780), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    font = _font(42)
    lines = (
        f"Patient: {_NAME}",
        f"Date of birth: {_BIRTH}",
        "Order number: 884422110099",
        "Analyte Result Reference Unit",
        "Albumin 4.5 g/dL 3.5-5.0",
    )
    for index, line in enumerate(lines):
        draw.text((40, 40 + index * 90), line, fill=(0, 0, 0), font=font)
    return image


def _ocr_text(payload: bytes) -> str:
    """Read an image twice, with the painter's page mode and the default mode."""
    import pytesseract

    with Image.open(BytesIO(payload)) as image:
        parts = [
            pytesseract.image_to_string(image, lang="eng+rus", config="--psm 6"),
            pytesseract.image_to_string(image, lang="eng+rus"),
        ]
    return "\n".join(str(part) for part in parts).casefold()


def _page_png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_masked_scan_hides_the_name_from_a_second_ocr() -> None:
    """A second OCR of the pages sent to the model does not see the name or birth date."""
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract is not installed")
    original = _image_pdf([_lab_page()])
    rendered = PdfiumRasterizer().render(original)
    source_text = _ocr_text(_page_png(rendered[0]))
    assert "anna" in source_text
    assert "synthetic" in source_text
    assert "1990" in source_text
    vision = RememberingVision()
    service = _service(vision, PdfiumScanRedactor())
    user = _user()
    result = await service.extract(user.id, original, client_key="203.0.113.10")
    if isinstance(result, RedactionPreview):
        hidden = _ocr_text(result.preview_png)
        assert "anna" not in hidden
        assert "synthetic" not in hidden
        assert "1990" not in hidden
        await service.confirm_redaction(user.id, result.token, client_key="203.0.113.10")
    assert vision.media_calls == 1
    assert vision.last_media is not None
    assert vision.last_media != original
    assert original not in vision.last_media
    delivered_pages = (
        (vision.last_media,)
        if vision.last_media_mime == "image/png"
        else tuple(_page_png(page) for page in PdfiumRasterizer().render(vision.last_media))
    )
    delivered = "\n".join(_ocr_text(page) for page in delivered_pages)
    assert "anna" not in delivered
    assert "synthetic" not in delivered
    assert "1990" not in delivered
