"""Levine 2018 phenotypic age, including the published worked numbers."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.services.phenoage import (
    RESEARCH_DISCLAIMER,
    CanonicalBiomarkers,
    LevineBiomarkers,
    PhenoAgeInputError,
    calculate_canonical_phenoage,
    calculate_levine_phenoage,
    score_confirmed_panel,
)

_WORKED_CANONICAL = {
    "albumin": 44.0,
    "creatinine": 1.53,
    "glucose": 105.0,
    "crp": 2.31,
    "lymphocyte": 24.0,
    "mcv": 97.0,
    "rdw": 11.8,
    "alp": 53.0,
    "wbc": 4.9,
}

# Supplement equation applied to the Cramer worksheet (Levine 2018):
# albumin 44 g/L, creatinine 135.25353 umol/L, glucose 5.8275 mmol/L,
# CRP 0.231 mg/dL, lymphocyte 24%, MCV 97 fL, RDW 11.8%, ALP 53 U/L,
# WBC 4.9 x10^3/uL, age 71. The worksheet prints xb -6.81, M 0.196, age 66.95.
_WORKED = LevineBiomarkers(
    albumin_g_l=44.0,
    creatinine_umol_l=135.25353,
    glucose_mmol_l=5.8275,
    crp_mg_dl=0.231,
    lymphocyte_percent=24.0,
    mcv_fl=97.0,
    rdw_percent=11.8,
    alp_u_l=53.0,
    wbc_10e3_per_ul=4.9,
    age_years=71.0,
)


def test_levine_2018_worked_example() -> None:
    """Phenotypic age matches the supplement equation on the published case."""
    result = calculate_levine_phenoage(_WORKED)
    assert result.linear_predictor == pytest.approx(-6.808633919031123)
    assert result.mortality_score_10yr == pytest.approx(0.19568843855085083)
    assert result.pheno_age == pytest.approx(66.95126185418155)
    assert round(result.linear_predictor, 2) == -6.81
    assert round(result.mortality_score_10yr, 3) == 0.196
    assert round(result.pheno_age, 2) == 66.95
    assert result.age_delta == pytest.approx(result.pheno_age - 71.0)
    assert result.disclaimer == RESEARCH_DISCLAIMER
    assert "not a medical service" in result.disclaimer


def test_dictionary_units_round_to_the_same_published_age() -> None:
    """mg/dL and mg/L inputs use the LOINC factors and still print 66.95."""
    result = calculate_canonical_phenoage(
        CanonicalBiomarkers(
            albumin_g_l=44.0,
            creatinine_mg_dl=1.53,
            glucose_mg_dl=105.0,
            crp_mg_l=2.31,
            lymphocyte_percent=24.0,
            mcv_fl=97.0,
            rdw_percent=11.8,
            alp_u_l=53.0,
            wbc_10e3_per_ul=4.9,
            age_years=71.0,
        )
    )
    assert round(result.pheno_age, 2) == 66.95
    assert round(result.mortality_score_10yr, 3) == 0.196


def test_confirmed_panel_matches_the_published_age_only_when_complete() -> None:
    """A gap is named. The missing value is not replaced, and the point is absent."""
    scored = score_confirmed_panel(_WORKED_CANONICAL, chronological_age=71.0)
    assert round(scored.pheno_age or 0, 2) == 66.95
    assert scored.age_delta == pytest.approx((scored.pheno_age or 0) - 71.0)
    assert scored.missing_markers == ()
    assert scored.disclaimer == RESEARCH_DISCLAIMER

    partial = score_confirmed_panel({"albumin": 44.0, "wbc": 4.9}, chronological_age=71.0)
    assert partial.pheno_age is None
    assert partial.age_delta is None
    assert partial.missing_markers[0] == "creatinine"
    assert "albumin" not in partial.missing_markers
    assert "wbc" not in partial.missing_markers

    no_age = score_confirmed_panel(_WORKED_CANONICAL, chronological_age=None)
    assert no_age.pheno_age is None
    assert no_age.missing_markers == ()


def test_unusable_crp_is_present_and_still_unscored() -> None:
    """Zero CRP is on the report. It is not listed as a missing marker."""
    markers = {**_WORKED_CANONICAL, "crp": 0.0}
    point = score_confirmed_panel(markers, chronological_age=71.0)
    assert point.pheno_age is None
    assert point.missing_markers == ()
    assert point.disclaimer == RESEARCH_DISCLAIMER


def test_non_positive_crp_is_rejected() -> None:
    """Natural log of CRP is undefined at zero."""
    markers = LevineBiomarkers(
        albumin_g_l=44.0,
        creatinine_umol_l=88.4,
        glucose_mmol_l=5.0,
        crp_mg_dl=0.0,
        lymphocyte_percent=30.0,
        mcv_fl=90.0,
        rdw_percent=13.0,
        alp_u_l=60.0,
        wbc_10e3_per_ul=6.0,
        age_years=40.0,
    )
    with pytest.raises(PhenoAgeInputError):
        calculate_levine_phenoage(markers)


def test_router_does_not_contain_the_formula() -> None:
    """DoD: HTTP controllers do not embed Levine coefficients."""
    source_path = Path(__file__).resolve().parents[1] / "api" / "phenoage.py"
    source = source_path.read_text(encoding="utf-8")
    for token in ("-19.9067", "0.0076927", "0.090165", "141.50225"):
        assert token not in source


async def test_phenoage_endpoint_returns_score_and_disclaimer() -> None:
    """POST /api/v1/phenoage returns the research index and the disclaimer."""
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/phenoage",
            json={
                "chronological_age": 71,
                "markers": {
                    "albumin": 44.0,
                    "creatinine": 1.53,
                    "glucose": 105.0,
                    "crp": 2.31,
                    "lymphocyte": 24.0,
                    "mcv": 97.0,
                    "rdw": 11.8,
                    "alp": 53.0,
                    "wbc": 4.9,
                },
            },
        )
    assert response.status_code == 200
    body = response.json()
    assert round(body["pheno_age"], 2) == 66.95
    assert body["disclaimer"] == RESEARCH_DISCLAIMER
    assert "mortality_score_10yr" not in body
    assert "full_name" not in body
    assert "date_of_birth" not in body


async def test_phenoage_endpoint_rejects_identity_fields() -> None:
    """A name on the request is not accepted."""
    application = create_app()
    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/phenoage",
            json={
                "chronological_age": 71,
                "full_name": "Ada Lovelace",
                "markers": {
                    "albumin": 44.0,
                    "creatinine": 1.53,
                    "glucose": 105.0,
                    "crp": 2.31,
                    "lymphocyte": 24.0,
                    "mcv": 97.0,
                    "rdw": 11.8,
                    "alp": 53.0,
                    "wbc": 4.9,
                },
            },
        )
    assert response.status_code == 422
