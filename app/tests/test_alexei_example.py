"""The fictional Alexei example on the home page matches the production engine.

The numbers are copied from src/data/alexeiExample.ts. If the engine or the
example changes, the published copy has to change with it.
"""

from __future__ import annotations

import pytest

from app.services.phenoage import CanonicalBiomarkers, calculate_canonical_phenoage

_START = CanonicalBiomarkers(
    albumin_g_l=42.0,
    creatinine_mg_dl=1.2,
    glucose_mg_dl=104.0,
    crp_mg_l=7.0,
    lymphocyte_percent=23.0,
    mcv_fl=92.0,
    rdw_percent=14.0,
    alp_u_l=80.0,
    wbc_10e3_per_ul=7.4,
    age_years=45.0,
)

_FOLLOW_UP = CanonicalBiomarkers(
    albumin_g_l=43.0,
    creatinine_mg_dl=1.12,
    glucose_mg_dl=99.0,
    crp_mg_l=3.0,
    lymphocyte_percent=26.0,
    mcv_fl=92.0,
    rdw_percent=13.7,
    alp_u_l=74.0,
    wbc_10e3_per_ul=6.8,
    age_years=45.3,
)


@pytest.mark.parametrize(
    ("markers", "published"),
    [(_START, 51.3), (_FOLLOW_UP, 47.0)],
)
def test_alexei_numbers_match_the_engine(markers: CanonicalBiomarkers, published: float) -> None:
    """The published one-decimal value is within 0.1 year of the engine."""
    result = calculate_canonical_phenoage(markers)
    assert result.pheno_age == pytest.approx(published, abs=0.1)
    assert round(result.pheno_age, 1) == published
