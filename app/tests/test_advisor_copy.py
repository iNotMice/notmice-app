"""Interface copy stays inside the wording of plan section 3.

The scan covers every i18n catalog and every component, not a short list of
screens. A new screen fails this test when it repeats a forbidden claim.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_I18N = _ROOT / "src" / "i18n"
_COMPONENTS = _ROOT / "src" / "components"
_ADVISOR_SOURCES = (
    _ROOT / "src" / "components" / "LifestyleLongevityAdvisor.tsx",
    _ROOT / "src" / "i18n" / "messages" / "en" / "lifestyleUi.ts",
    _ROOT / "src" / "i18n" / "messages" / "de" / "lifestyleUi.ts",
)
_REMOVED_RECOMMENDATIONS = (
    _ROOT / "src" / "data" / "lifestyleInterventions.ts",
    _ROOT / "src" / "i18n" / "lifestyleIds.ts",
    _ROOT / "src" / "i18n" / "messages" / "en" / "lifestyle.ts",
    _ROOT / "src" / "i18n" / "messages" / "de" / "lifestyle.ts",
)
_MARKER_IDS = (
    "albumin",
    "creatinine",
    "glucose",
    "crp",
    "lymphocyte",
    "mcv",
    "rdw",
    "alp",
    "wbc",
)
_JOURNAL_FILES = {
    "src/i18n/messages/en/journal.ts",
    "src/i18n/messages/de/journal.ts",
}
# Field names and kind ids. The visible labels live in the journal catalogs.
_CODE_TOKENS = frozenset({"supplement", "drug", "nutrition", "activity", "sleep", "other", "dose"})
_QUOTE = re.compile(r"'((?:\\'|[^'])*)'|\"((?:\\\"|[^\"])*)\"|`((?:\\`|[^`])*)`")
_NEGATED_RECOMMENDATION = re.compile(
    r"not (?:a |an ).{0,80}recommend|keine .{0,80}empfehl|nicht .{0,40}empfehl",
    re.IGNORECASE,
)
_JOURNAL_HOWTO = re.compile(
    r"\b(dose|dosis)\b",
    re.IGNORECASE,
)

# Left column of section 3, the status words removed from the storefront,
# and the same claims in the languages the interface speaks.
_FORBIDDEN = (
    r"опасно",
    r"высокий риск",
    r"тревожно",
    r"оптимум",
    r"норма",
    r"вы сохранили",
    r"ваш риск",
    r"рекомендуем",
    r"попробуйте добавить",
    r"это сработало",
    r"эффект препарата",
    r"high[\s-]?risk",
    r"optim(?:al\w*|um)\b",
    r"(?<!-)\bnormal(?:e|en|er|es)?\b",
    r"\belevated\b",
    r"\berhöht\w*\b",
    r"\bimpaired\b",
    r"\beuglyc",
    r"percentile",
    r"perzentil",
    r"перцентиль",
    r"mortalit",
    r"\bhazard\b",
    r"protective",
    r"accelerant",
    r"schützend",
    r"beschleunigend",
    r"heavy positive",
    r"stark positiv",
    r"years saved",
    r"saved years",
    r"\byour risk\b",
    r"\brecommend",
    r"\bsupplement\b",
    r"\bdose\b",
    r"\bdoses\b",
    r"add to (?:your |the )?diet",
    r"this worked",
    r"drug effect",
    r"hohes risiko",
    r"\brisk\b",
    r"\brisiko\b",
    r"empfehl",
    r"ergänzung",
    r"\bdosis\b",
    r"jahre gespart",
    r"gefähr",
    r"alarm",
)
_JOURNAL_PATTERNS = frozenset(
    {
        r"\bsupplement\b",
        r"\bdose\b",
        r"\bdoses\b",
        r"ergänzung",
        r"\bdosis\b",
    }
)
_RECOMMENDATION_PATTERNS = frozenset({r"\brecommend", r"empfehl"})


def _sources() -> list[Path]:
    """Every catalog and component the interface can render."""
    files = [
        path
        for root in (_I18N, _COMPONENTS)
        for path in root.rglob("*")
        if path.suffix in {".ts", ".tsx"} and path.is_file()
    ]
    if not files:
        raise AssertionError("interface sources missing")
    return files


def _quoted(text: str) -> list[str]:
    """String literals on one line. Template holes are not part of the text."""
    found: list[str] = []
    for match in _QUOTE.finditer(text):
        literal = next(group for group in match.groups() if group is not None)
        literal = literal.replace("\\'", "'").replace('\\"', '"')
        parts = re.split(r"\$\{[^}]*\}", literal)
        found.extend(part for part in parts if re.search(r"[A-Za-z\u0400-\u04FF]", part))
    return found


def _skipped_patterns(relative: str, literal: str) -> frozenset[str]:
    """Journal vocabulary and a disclaimer that names what the product is not."""
    skipped: set[str] = set()
    posix = relative.replace("\\", "/")
    journal_howto = posix.endswith("instructions.ts") and _JOURNAL_HOWTO.search(literal)
    if posix in _JOURNAL_FILES or journal_howto:
        skipped.update(_JOURNAL_PATTERNS)
    if _NEGATED_RECOMMENDATION.search(literal):
        skipped.update(_RECOMMENDATION_PATTERNS)
    return frozenset(skipped)


def _hits() -> list[str]:
    """Forbidden claims still present in copy a person can read."""
    found: list[str] = []
    for path in _sources():
        relative = path.relative_to(_ROOT).as_posix()
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for literal in _quoted(line):
                if literal.strip() in _CODE_TOKENS:
                    continue
                skipped = _skipped_patterns(relative, literal)
                for pattern in _FORBIDDEN:
                    if pattern in skipped:
                        continue
                    if re.search(pattern, literal, flags=re.IGNORECASE):
                        snippet = literal.replace("\n", " ")
                        if len(snippet) > 140:
                            snippet = snippet[:137] + "..."
                        found.append(f"{relative}:{line_number}: /{pattern}/: {snippet}")
    return found


def test_interface_copy_omits_section_3_forbidden_claims() -> None:
    """Catalogs and components omit the claims listed in section 3."""
    assert _hits() == []


def test_advisor_cards_are_static_marker_notes() -> None:
    """Nine prepared marker notes, a laboratory interval, and the Levine 2018 citation."""
    text = "\n".join(path.read_text(encoding="utf-8") for path in _ADVISOR_SOURCES)
    for marker_id in _MARKER_IDS:
        assert marker_id in text
    assert "reference interval" in text
    assert "Referenzintervall" in text
    assert text.count("https://doi.org/10.18632/aging.101414") == 2
    assert "dataDisclaimer" in text
    assert "LIFESTYLE_KNOWLEDGE_BASE" not in text
    assert "estimatedPheno" not in text
    english = (_ROOT / "src" / "i18n" / "messages" / "en" / "shell.ts").read_text(encoding="utf-8")
    german = (_ROOT / "src" / "i18n" / "messages" / "de" / "shell.ts").read_text(encoding="utf-8")
    assert "self-observation tool for research purposes" in english
    assert "Werkzeug zur Selbstbeobachtung für Forschungszwecke" in german


@pytest.mark.parametrize("path", _REMOVED_RECOMMENDATIONS)
def test_personalized_recommendation_sources_are_gone(path: Path) -> None:
    """Dose and diet protocols are not left where the advisor can render them."""
    assert not path.exists()
