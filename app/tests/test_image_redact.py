"""Photo redaction: paint the header locally, then let the model see only that frame."""

from __future__ import annotations

import os
import shutil
from datetime import UTC, datetime
from io import BytesIO
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from PIL import Image, ImageDraw, ImageFont
from structlog.testing import capture_logs

from app.domain.accounts import UserRecord
from app.domain.uploads import ExtractSessionNotFoundError
from app.services.extract_sessions import InMemoryExtractSessionStore
from app.services.image_redact import (
    LabImageRedactor,
    OcrWord,
    PassthroughImageRedactor,
    RedactedImage,
    TesseractImageRedactor,
)
from app.services.uploads import RedactionPreview, UploadService
from app.services.vision import ProviderExtraction
from app.tests.test_uploads import (
    FakeVision,
    InMemoryLabStore,
    _account_service,
    _app,
    _budget,
    _done,
)

_NAME = "Anna Synthetic"
_BIRTH = "1990-01-01"


class RememberingVision(FakeVision):
    """Keeps the media bytes so a test can OCR what the model would receive."""

    def __init__(self) -> None:
        super().__init__()
        self.last_media: bytes | None = None

    async def extract_from_media(self, payload: bytes, mime_type: str) -> ProviderExtraction:
        self.last_media = payload
        return await super().extract_from_media(payload, mime_type)


class ScriptedReader:
    """Returns a fixed page of words, then a page with the header gone."""

    def __init__(self, first: tuple[OcrWord, ...], later: tuple[OcrWord, ...]) -> None:
        self._first = first
        self._later = later
        self.calls = 0

    def read(self, image: Image.Image) -> tuple[OcrWord, ...]:
        del image
        self.calls += 1
        if self.calls == 1:
            return self._first
        return self._later


class PreviewRedactor:
    """Always asks the person to confirm, and returns a stand-in PNG."""

    def __init__(self, painted: bytes) -> None:
        self._painted = painted
        self.seen: list[bytes] = []

    def redact(self, payload: bytes, mime_type: str) -> RedactedImage:
        del mime_type
        self.seen.append(payload)
        return RedactedImage(
            payload=self._painted,
            mime_type="image/png",
            region_count=2,
            needs_confirmation=True,
        )


def _service(vision: FakeVision, redactor: LabImageRedactor | None = None) -> UploadService:
    return UploadService(
        vision=vision,
        sessions=InMemoryExtractSessionStore(ttl_seconds=60),
        lab_results=InMemoryLabStore(),
        max_upload_bytes=2_000_000,
        budget=_budget(),
        image_redactor=redactor if redactor is not None else PassthroughImageRedactor(),
    )


def _user() -> UserRecord:
    return UserRecord(id=uuid4(), public_id="nmtest", is_public=False, created_at=datetime.now(UTC))


def _word(text: str, *, left: int, top: int, confidence: float) -> OcrWord:
    return OcrWord(text=text, confidence=confidence, left=left, top=top, width=80, height=28)


def _blank() -> Image.Image:
    return Image.new("RGB", (400, 220), (255, 255, 255))


def _png(image: Image.Image) -> bytes:
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


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


@pytest.mark.asyncio
async def test_confident_paint_is_what_the_model_receives() -> None:
    """The model payload is the painted PNG, and the name box is black."""
    image = _blank()
    reader = ScriptedReader(_header_words(0.95), _table_words())
    vision = RememberingVision()
    service = _service(vision, TesseractImageRedactor(reader))
    with capture_logs() as logs:
        completed = _done(await service.extract(_user().id, _png(image), client_key="203.0.113.10"))
    assert vision.media_calls == 1
    assert vision.text_calls == 0
    assert vision.last_media_mime == "image/png"
    assert vision.last_media is not None
    assert vision.last_media != _png(image)
    painted = Image.open(BytesIO(vision.last_media))
    assert painted.getpixel((40, 28)) == (0, 0, 0)
    assert completed.session.panel.document_sha256
    assert all("Anna" not in str(event.values()) for event in logs)
    assert any(
        event.get("event") == "image_redacted" and event.get("region_count") == 1 for event in logs
    )


@pytest.mark.asyncio
async def test_uncertain_paint_waits_for_the_person() -> None:
    """A weak read does not call the model and does not reject the upload."""
    image = _blank()
    reader = ScriptedReader(_header_words(0.2), _table_words())
    vision = RememberingVision()
    service = _service(vision, TesseractImageRedactor(reader))
    user = _user()
    with capture_logs() as logs:
        preview = await service.extract(user.id, _png(image), client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    assert preview.region_count == 1
    assert vision.media_calls == 0
    assert all("Anna" not in str(event.values()) for event in logs)
    painted = Image.open(BytesIO(preview.preview_png))
    assert painted.getpixel((40, 28)) == (0, 0, 0)
    completed = await service.confirm_redaction(
        user.id,
        preview.token,
        client_key="203.0.113.10",
    )
    assert vision.media_calls == 1
    assert vision.last_media == preview.preview_png
    assert completed.session.panel.document_sha256
    assert completed.session.panel.markers


@pytest.mark.asyncio
async def test_discard_drops_the_frame_without_a_model_call() -> None:
    """Cancel frees the painted frame. A later confirm does not extract it."""
    painted = _png(_blank())
    redactor = PreviewRedactor(painted)
    vision = RememberingVision()
    service = _service(vision, redactor)
    user = _user()
    original = b"\xff\xd8\xff\xe0" + b"\x10" * 24
    preview = await service.extract(user.id, original, client_key="203.0.113.10")
    assert isinstance(preview, RedactionPreview)
    assert redactor.seen == [original]
    service.discard_redaction(user.id, preview.token)
    assert vision.media_calls == 0
    with pytest.raises(ExtractSessionNotFoundError):
        await service.confirm_redaction(user.id, preview.token, client_key="203.0.113.10")


@pytest.mark.asyncio
async def test_http_confirm_sends_only_the_painted_frame() -> None:
    """202 carries the painted PNG. Confirm is the first model call."""
    painted = _png(Image.new("RGB", (8, 8), (0, 0, 0)))
    redactor = PreviewRedactor(painted)
    vision = RememberingVision()
    service = _service(vision, redactor)
    application = _app(_account_service(), service)
    original = b"\xff\xd8\xff\xe0" + b"\x33" * 24
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        created = await client.post("/api/v1/accounts", json={})
        token = created.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        extracted = await client.post(
            "/api/v1/uploads/extract",
            headers=headers,
            files={"file": ("scan.jpg", original, "image/jpeg")},
        )
        assert extracted.status_code == 202
        body = extracted.json()
        assert body["region_count"] == 2
        assert "preview_png" in body
        assert vision.media_calls == 0
        confirmed = await client.post(
            "/api/v1/uploads/redaction/confirm",
            headers=headers,
            json={"redaction_token": body["redaction_token"]},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["document_sha256"] != ""
        assert vision.media_calls == 1
        assert vision.last_media == painted
        assert vision.last_media != original


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


def _lab_fixture() -> bytes:
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
    return _png(image)


def _ocr_text(payload: bytes) -> str:
    """Read the image twice, with the painter's page mode and the default mode."""
    import pytesseract

    with Image.open(BytesIO(payload)) as image:
        parts = [
            pytesseract.image_to_string(image, lang="eng+rus", config="--psm 6"),
            pytesseract.image_to_string(image, lang="eng+rus"),
        ]
    return "\n".join(str(part) for part in parts).casefold()


@pytest.mark.asyncio
async def test_masked_fixture_hides_the_name_from_a_second_ocr() -> None:
    """A second OCR of the bytes sent to the model does not see the synthetic name or birth date."""
    if shutil.which("tesseract") is None:
        pytest.skip("tesseract is not installed")
    original = _lab_fixture()
    source_text = _ocr_text(original)
    assert "anna" in source_text
    assert "synthetic" in source_text
    assert "1990" in source_text
    vision = RememberingVision()
    service = _service(vision, TesseractImageRedactor())
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
    delivered = _ocr_text(vision.last_media)
    assert "anna" not in delivered
    assert "synthetic" not in delivered
    assert "1990" not in delivered
