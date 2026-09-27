"""In-memory PDF text extraction. The original bytes never touch disk.

Selectable lab reports are cut per page before any model call: the repeating
page header and the footer (name, order number, barcode) stay out of the
payload. A line filter is the second check on whatever text remains.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

import pdfplumber

from app.domain.pii import contains_contact_text, contains_person_name

MIN_SELECTABLE_TEXT_CHARS = 80

# A results-table heading names at least two of these. Stems match
# «референсный» and «results»; exact words avoid clipping ordinary prose.
_HEADER_STEMS: tuple[str, ...] = (
    "показател",
    "результат",
    "референс",
    "единиц",
    "наименован",
    "значен",
    "исследован",
    "analyte",
    "result",
    "reference",
    "unit",
    "interval",
)
_HEADER_EXACT: frozenset[str] = frozenset({"норма", "test", "tests", "flag"})
_HEADER_HITS_REQUIRED = 2

_PERSONAL_PHRASES: tuple[str, ...] = (
    "дата рождения",
    "date of birth",
    "birth date",
    "номер заказа",
    "order number",
    "order no",
    "медицинская карта",
)
_PERSONAL_WORDS: frozenset[str] = frozenset(
    {
        "пациент",
        "фио",
        "фамилия",
        "patient",
        "штрихкод",
        "barcode",
        "полис",
        "телефон",
        "phone",
        "email",
        "паспорт",
        "заказ",
    }
)

_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_PAGE_RE = re.compile(
    r"^(?:page\s+\d+(?:\s+of\s+\d+)?|стр\.?\s*\d+(?:\s+из\s+\d+)?|\d+\s*/\s*\d+)$",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    r"(?:"
    r"g/dl|g/l|mg/dl|mg/l|mmol/l|umol/l|µmol/l|ng/ml|pg/ml|iu/l|u/l|"
    r"г/л|мг/дл|ммоль/л|мкмоль/л|нг/мл|пг/мл|ед/л|"  # noqa: RUF001
    r"(?<![a-zа-яё])(?:fl|pg)"  # noqa: RUF001
    r"|%"
    r")",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SelectablePdf:
    """Text PDF that is long enough to structure without sending the file.

    ``model_text`` has already lost per-page headers and footers. It is the
    only PDF text that may be sent to an external model.
    """

    model_text: str
    page_count: int
    dropped_lines: int


def extract_pdf_text(payload: bytes) -> str:
    """Return concatenated selectable text from a PDF held in RAM.

    This is the raw text, including page headers. Model calls use
    ``prepare_selectable_pdf`` instead.

    Args:
        payload: Complete PDF bytes. Must not be written to a path.
    """
    return "\n".join(page for page in _extract_pages(payload) if page)


def has_selectable_text(payload: bytes) -> bool:
    """Return True when the PDF has enough text to skip Vision OCR.

    Args:
        payload: Complete PDF bytes.
    """
    return len(extract_pdf_text(payload)) >= MIN_SELECTABLE_TEXT_CHARS


def prepare_selectable_pdf(payload: bytes) -> SelectablePdf | None:
    """Return redacted page text, or None when the PDF is not a text report.

    A text report is never a reason to send the original bytes. When every
    line is header or footer, ``model_text`` is empty and the caller must
    stop before the model.

    Args:
        payload: Complete PDF bytes. Must not be written to a path.
    """
    pages = _extract_pages(payload)
    raw = "\n".join(page for page in pages if page)
    if len(raw) < MIN_SELECTABLE_TEXT_CHARS:
        return None
    model_text, dropped_lines = redact_lab_pages(pages)
    return SelectablePdf(
        model_text=model_text,
        page_count=len(pages),
        dropped_lines=dropped_lines,
    )


def redact_lab_pages(pages: list[str]) -> tuple[str, int]:
    """Drop headers and footers on each page, then join what remains.

    Args:
        pages: Selectable text of each page, in order.

    Returns:
        Model-safe text and how many non-empty lines were removed.
    """
    kept_pages: list[str] = []
    dropped = 0
    for page in pages:
        redacted, page_dropped = redact_lab_page(page)
        dropped += page_dropped
        if redacted:
            kept_pages.append(redacted)
    return "\n".join(kept_pages), dropped


def redact_lab_page(page: str) -> tuple[str, int]:
    """Keep the results table on one page and drop the chrome around it.

    Lines above the first results heading are the page header. Lines at the
    bottom that carry a name, order number, barcode, or page number are the
    footer. Any personal line that survives those cuts is removed as well,
    unless it is itself a measured row.

    Args:
        page: Selectable text of a single page.

    Returns:
        Kept text and how many non-empty lines were removed.
    """
    original = [line.strip() for line in page.splitlines() if line.strip()]
    lines = list(original)
    header_at = _table_header_index(lines)
    if header_at is not None:
        lines = lines[header_at:]
    while lines and _is_chrome_line(lines[-1]):
        lines.pop()
    kept = [line for line in lines if not _is_chrome_line(line)]
    return "\n".join(kept), len(original) - len(kept)


def _extract_pages(payload: bytes) -> list[str]:
    """Read each page's selectable text without writing the PDF to disk."""
    pages: list[str] = []
    with pdfplumber.open(BytesIO(payload)) as document:
        for page in document.pages:
            pages.append((page.extract_text() or "").strip())
    return pages


def _table_header_index(lines: list[str]) -> int | None:
    """Return the first line that looks like a results-table heading."""
    for index, line in enumerate(lines):
        if _is_result_line(line):
            continue
        if _header_hits(line) >= _HEADER_HITS_REQUIRED:
            return index
    return None


def _header_hits(line: str) -> int:
    """Count distinct heading words on ``line``."""
    hits: set[str] = set()
    for word in _words(line):
        if word in _HEADER_EXACT:
            hits.add(word)
            continue
        for stem in _HEADER_STEMS:
            if word.startswith(stem):
                hits.add(stem)
                break
    return len(hits)


def _words(line: str) -> list[str]:
    """Return Unicode letter-words, lowercased."""
    return [word.casefold() for word in _WORD_RE.findall(line)]


def _is_chrome_line(line: str) -> bool:
    """Return True when a line is page chrome rather than a measured row."""
    if _is_result_line(line) or _header_hits(line) >= _HEADER_HITS_REQUIRED:
        return False
    if _PAGE_RE.match(line.strip()):
        return True
    if _is_barcode(line):
        return True
    folded = line.casefold()
    if any(phrase in folded for phrase in _PERSONAL_PHRASES):
        return True
    if any(_has_word(folded, word) for word in _PERSONAL_WORDS):
        return True
    if contains_contact_text(line) or contains_person_name(line):
        return True
    return False


def _has_word(folded: str, word: str) -> bool:
    """Return True when ``word`` appears as its own word in ``folded``."""
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", folded) is not None


def _is_barcode(line: str) -> bool:
    """Return True when the line is a long digit run, ignoring spaces and stars."""
    compact = re.sub(r"[\s*\-]+", "", line)
    return compact.isdigit() and len(compact) >= 10


def _is_result_line(line: str) -> bool:
    """Return True when the line carries a number and a printed unit."""
    if not re.search(r"\d", line):
        return False
    return _UNIT_RE.search(line) is not None
