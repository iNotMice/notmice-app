"""Advisor screen copy stays inside the wording of plan section 3."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
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

# Left column of section 3, plus the same claims in the languages the screen speaks.
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
    r"\boptimal\b",
    r"\boptimum\b",
    r"\bnormal\b",
    r"years saved",
    r"saved years",
    r"\byour risk\b",
    r"\brecommend",
    r"supplement",
    r"\bdose\b",
    r"\bdoses\b",
    r"add to (?:your |the )?diet",
    r"this worked",
    r"drug effect",
    r"hohes risiko",
    r"\brisk\b",
    r"\brisiko\b",
    r"empfehl",
    r"ergänz",
    r"\bdosis\b",
    r"jahre gespart",
    r"gefähr",
    r"alarm",
)


def _advisor_text() -> str:
    missing = [path for path in _ADVISOR_SOURCES if not path.is_file()]
    if missing:
        joined = ", ".join(str(path.relative_to(_ROOT)) for path in missing)
        raise AssertionError(f"advisor sources missing: {joined}")
    return "\n".join(path.read_text(encoding="utf-8") for path in _ADVISOR_SOURCES)


def test_advisor_copy_omits_section_3_forbidden_claims() -> None:
    """The advisor screen does not use the claims listed in the left column of section 3."""
    text = _advisor_text()
    hits = [pattern for pattern in _FORBIDDEN if re.search(pattern, text, flags=re.IGNORECASE)]
    assert hits == []


def test_advisor_cards_are_static_marker_notes() -> None:
    """Nine prepared marker notes, a laboratory interval, and the Levine 2018 citation."""
    text = _advisor_text()
    for marker_id in _MARKER_IDS:
        assert marker_id in text
    assert "reference interval" in text
    assert "Referenzintervall" in text
    assert text.count("https://doi.org/10.18632/aging.101414") == 2
    assert "self-observation tool for research purposes" in text
    assert "Werkzeug zur Selbstbeobachtung für Forschungszwecke" in text
    assert "LIFESTYLE_KNOWLEDGE_BASE" not in text
    assert "estimatedPheno" not in text


@pytest.mark.parametrize("path", _REMOVED_RECOMMENDATIONS)
def test_personalized_recommendation_sources_are_gone(path: Path) -> None:
    """Dose and diet protocols are not left where the advisor can render them."""
    assert not path.exists()
