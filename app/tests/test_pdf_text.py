"""pdfplumber RAM extraction and per-page header removal."""

# Cyrillic units in the synthetic blanks are intentional, not homoglyph typos.
# ruff: noqa: RUF001

from __future__ import annotations

from app.services.pdf_text import (
    extract_pdf_text,
    has_selectable_text,
    prepare_selectable_pdf,
    redact_lab_page,
)
from app.tests.test_uploads import _multipage_lab_pdf, _text_pdf


def test_pdfplumber_reads_bytes_from_memory() -> None:
    """A text PDF yields the printed analytes without a filesystem path."""
    payload = _text_pdf(
        "Serum Albumin 46.2 g/L  Creatinine 0.88 mg/dL  Glucose 84 mg/dL extra padding text"
    )
    text = extract_pdf_text(payload)
    assert "Albumin" in text
    assert has_selectable_text(payload) is True


def test_image_like_pdf_without_text_is_not_selectable() -> None:
    """A PDF wrapper with almost no text should fall through to Vision."""
    payload = _text_pdf("x")
    assert has_selectable_text(payload) is False
    assert prepare_selectable_pdf(payload) is None


def test_redact_lab_page_keeps_rows_and_drops_russian_chrome() -> None:
    """A Cyrillic blank loses the repeating name, birth date, order, and barcode."""
    page = "\n".join(
        [
            "Лаборатория Олимп",
            "Пациент: Иванов Иван Иванович",
            "Дата рождения: 15.03.1984",
            "Номер заказа: 88442211",
            "Показатель Результат Единицы Референс",
            "Альбумин 46.2 г/л 35-52",
            "Креатинин 78 мкмоль/л 62-106",
            "Иванов Иван Иванович",
            "Номер заказа: 88442211",
            "88442211009988",
            "Стр. 1 из 2",
        ]
    )
    redacted, dropped = redact_lab_page(page)
    assert "Альбумин" in redacted
    assert "Креатинин" in redacted
    assert "Показатель" in redacted
    assert "Иванов" not in redacted
    assert "15.03.1984" not in redacted
    assert "88442211" not in redacted
    assert "Олимп" not in redacted
    assert dropped >= 7


def test_continuation_page_without_column_header_still_drops_the_name() -> None:
    """A later page may repeat the patient block without repeating the column titles."""
    page = "\n".join(
        [
            "Пациент: Иванов Иван Иванович",
            "Дата рождения: 15.03.1984",
            "Глюкоза 5.1 ммоль/л 4.1-5.9",
            "Иванов Иван Иванович",
            "Стр. 2 из 2",
        ]
    )
    redacted, _dropped = redact_lab_page(page)
    assert "Глюкоза" in redacted
    assert "Иванов" not in redacted
    assert "15.03.1984" not in redacted


def test_multipage_pdf_redacts_every_page() -> None:
    """The fixture blank repeats identity on both pages; neither page reaches the model text."""
    prepared = prepare_selectable_pdf(_multipage_lab_pdf())
    assert prepared is not None
    assert prepared.page_count == 2
    assert prepared.dropped_lines > 0
    assert "Serum Albumin" in prepared.model_text
    assert "Glucose" in prepared.model_text
    assert "Ivanov" not in prepared.model_text
    assert "88442211" not in prepared.model_text
    assert "Page 1 of 2" not in prepared.model_text
    assert "Page 2 of 2" not in prepared.model_text
