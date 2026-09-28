"""LOINC dictionary loading, synonym match, unit conversion, and typo window."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.enums import MappingStatus
from app.domain.loinc import PHENOAGE_LOINC, LoincDictionary, LoincDictionaryError
from app.domain.uploads import RawMarker, map_marker
from app.services.loinc_dictionary import load_loinc_dictionary


def test_dictionary_has_phenoage_codes_and_twenty_markers() -> None:
    """Nine Levine codes stay put, and the catalog meets the 20-marker bar."""
    dictionary = load_loinc_dictionary()
    assert dictionary.dictionary_id == "notmice-loinc"
    assert dictionary.version == "1.0.0"
    assert dictionary.license == "CC-BY-4.0"
    assert len(dictionary.entries) >= 20
    by_id = {entry.entry_id: entry for entry in dictionary.entries}
    for marker_id, loinc in PHENOAGE_LOINC.items():
        entry = by_id[marker_id]
        assert entry.loinc == loinc
        assert entry.phenoage is True


def test_albumin_english_and_russian_names() -> None:
    """DoD: Serum Albumin and Альбумин both resolve to 1751-7."""
    dictionary = load_loinc_dictionary()
    for name in ("Serum Albumin", "Альбумин"):
        mapped = map_marker(RawMarker(raw_name=name, value=46.0, unit="g/L"), dictionary)
        assert mapped.canonical_id == "albumin"
        assert mapped.loinc_code == "1751-7"
        assert mapped.mapping_status is MappingStatus.MAPPED
        assert mapped.within_range is True
        assert mapped.unit == "g/L"


def test_review_screen_names_map_to_the_nine() -> None:
    """The confirm form's display names, including the parenthetical, stay mapped."""
    dictionary = load_loinc_dictionary()
    names = {
        "Serum Albumin": "albumin",
        "Serum Creatinine": "creatinine",
        "Fasting Serum Glucose": "glucose",
        "hs-C-Reactive Protein": "crp",
        "Lymphocyte Percentage": "lymphocyte",
        "Mean Corpuscular Volume (MCV)": "mcv",
        "Red Cell Distribution Width (RDW)": "rdw",
        "Alkaline Phosphatase (ALP)": "alp",
        "White Blood Cell Count (WBC)": "wbc",
    }
    for raw_name, canonical_id in names.items():
        mapped = map_marker(RawMarker(raw_name=raw_name, value=10.0, unit="g/L"), dictionary)
        assert mapped.canonical_id == canonical_id


def test_unknown_name_is_not_dropped() -> None:
    """A name outside the dictionary stays on the unmapped queue with its value."""
    dictionary = load_loinc_dictionary()
    mapped = map_marker(RawMarker(raw_name="Vitamin D", value=42.0, unit="ng/mL"), dictionary)
    assert mapped.mapping_status is MappingStatus.UNMAPPED
    assert mapped.canonical_id is None
    assert mapped.loinc_code is None
    assert mapped.value == Decimal("42")
    assert mapped.unit == "ng/mL"


def test_creatinine_micromoles_convert_to_canonical_unit() -> None:
    """88.4 µmol/L is 1.0 mg/dL, the PhenoAge unit for creatinine."""
    dictionary = load_loinc_dictionary()
    mapped = map_marker(RawMarker(raw_name="Креатинин", value=88.4, unit="мкмоль/л"), dictionary)
    assert mapped.loinc_code == "2160-0"
    assert mapped.unit == "mg/dL"
    assert mapped.value == Decimal("1")
    assert mapped.within_range is True


def test_hemoglobin_grams_per_decilitre_scale_to_grams_per_litre() -> None:
    """A US hemoglobin unit is scaled into the dictionary canonical unit."""
    dictionary = load_loinc_dictionary()
    mapped = map_marker(RawMarker(raw_name="Hemoglobin", value=14.5, unit="g/dL"), dictionary)
    assert mapped.loinc_code == "718-7"
    assert mapped.unit == "g/L"
    assert mapped.value == Decimal("145")
    assert mapped.within_range is True


def test_implausible_value_stays_mapped_and_flagged() -> None:
    """A typo such as 460 g/L is kept for review and marked outside the window."""
    dictionary = load_loinc_dictionary()
    mapped = map_marker(RawMarker(raw_name="Albumin", value=460.0, unit="g/L"), dictionary)
    assert mapped.mapping_status is MappingStatus.MAPPED
    assert mapped.loinc_code == "1751-7"
    assert mapped.value == Decimal("460")
    assert mapped.within_range is False


def test_unknown_unit_is_not_rescaled() -> None:
    """An unrecognised unit keeps the original number and skips the range check."""
    dictionary = load_loinc_dictionary()
    mapped = map_marker(RawMarker(raw_name="Albumin", value=46.0, unit="bananas"), dictionary)
    assert mapped.loinc_code == "1751-7"
    assert mapped.unit == "bananas"
    assert mapped.value == Decimal("46")
    assert mapped.within_range is None


def test_dictionary_rejects_snomed_and_short_catalogs() -> None:
    """Phase 2 accepts LOINC only, and a stub catalog cannot pass as v1."""
    with pytest.raises(LoincDictionaryError):
        LoincDictionary.from_payload(
            {
                "id": "bad",
                "version": "0",
                "license": "CC-BY-4.0",
                "standard": "LOINC",
                "snomed": True,
                "markers": [],
            }
        )
