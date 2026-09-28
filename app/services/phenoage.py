"""PhenoAge research index from Levine et al., Aging 2018.

The formula is the Gompertz phenotypic age in the supplement of
Levine ME et al., Aging (Albany NY). 2018;10(4):573-591.
Coefficients are Table 1 / Supplementary Table S1. Gamma is the
unrounded methods value 0.0076927, not the table's 0.0077.
Alkaline phosphatase uses the printed weight 0.0019.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.domain.cabinet import missing_phenoage_markers

# Levine units and weights (Table 1, Supplementary Table S1).
_INTERCEPT = -19.9067
_ALBUMIN_G_L = -0.0336
_CREATININE_UMOL_L = 0.0095
_GLUCOSE_MMOL_L = 0.1953
_LN_CRP_MG_DL = 0.0954
_LYMPHOCYTE_PERCENT = -0.0120
_MCV_FL = 0.0268
_RDW_PERCENT = 0.3306
_ALP_U_L = 0.0019
_WBC_10E3_PER_UL = 0.0554
_AGE_YEARS = 0.0804

# Supplement methods: gamma, 120-month horizon, and the age inversion.
_GAMMA = 0.0076927
_HORIZON_MONTHS = 120
_PHENO_INTERCEPT = 141.50225
_PHENO_LN_SCALE = -0.00553
_PHENO_DIVISOR = 0.090165

# Same factors as the LOINC dictionary canonical units.
_CREATININE_UMOL_PER_MG_DL = Decimal("88.4")
_GLUCOSE_MMOL_PER_MG_DL = Decimal("0.0555")
_CRP_MG_DL_PER_MG_L = Decimal("0.1")

RESEARCH_DISCLAIMER = (
    "PhenoAge is a research index (Levine et al., Aging 2018), "
    "not a medical service, diagnosis, or treatment recommendation."
)


class PhenoAgeInputError(ValueError):
    """Raised when a biomarker set cannot be scored."""


@dataclass(frozen=True, slots=True)
class LevineBiomarkers:
    """Nine markers in the units the 2018 coefficients were fit on, plus age."""

    albumin_g_l: float
    creatinine_umol_l: float
    glucose_mmol_l: float
    crp_mg_dl: float
    lymphocyte_percent: float
    mcv_fl: float
    rdw_percent: float
    alp_u_l: float
    wbc_10e3_per_ul: float
    age_years: float


@dataclass(frozen=True, slots=True)
class CanonicalBiomarkers:
    """Nine markers in LOINC-dictionary units, plus age in years.

    Albumin is g/L, creatinine and glucose are mg/dL, CRP is mg/L.
    The remaining five markers already match the Levine units.
    """

    albumin_g_l: float
    creatinine_mg_dl: float
    glucose_mg_dl: float
    crp_mg_l: float
    lymphocyte_percent: float
    mcv_fl: float
    rdw_percent: float
    alp_u_l: float
    wbc_10e3_per_ul: float
    age_years: float


@dataclass(frozen=True, slots=True)
class PhenoAgeResult:
    """Published outputs of the phenotypic-age transform."""

    chronological_age: float
    pheno_age: float
    age_delta: float
    mortality_score_10yr: float
    linear_predictor: float
    disclaimer: str


def calculate_levine_phenoage(markers: LevineBiomarkers) -> PhenoAgeResult:
    """Score biomarkers that are already in Levine 2018 units.

    Args:
        markers: Albumin in g/L, creatinine in µmol/L, glucose in mmol/L,
            CRP in mg/dL, and the other five markers in their printed units.

    Returns:
        Ten-year mortality probability and the phenotypic age in years.

    Raises:
        PhenoAgeInputError: A value is non-finite or CRP is not positive.
    """
    _require_finite(markers)
    if markers.crp_mg_dl <= 0:
        raise PhenoAgeInputError("C-reactive protein must be positive")
    xb = _linear_predictor(markers)
    mortality = _ten_year_mortality(xb)
    pheno_age = _phenotypic_age(mortality)
    return PhenoAgeResult(
        chronological_age=markers.age_years,
        pheno_age=pheno_age,
        age_delta=pheno_age - markers.age_years,
        mortality_score_10yr=mortality,
        linear_predictor=xb,
        disclaimer=RESEARCH_DISCLAIMER,
    )


@dataclass(frozen=True, slots=True)
class ConfirmedPanelPhenoAge:
    """One cabinet point. A missing marker is listed and is not filled in."""

    pheno_age: float | None
    age_delta: float | None
    missing_markers: tuple[str, ...]
    disclaimer: str


def score_confirmed_panel(
    markers: Mapping[str, float],
    *,
    chronological_age: float | None,
) -> ConfirmedPanelPhenoAge:
    """Score one confirmed panel, or name the Levine markers it does not have.

    Args:
        markers: Canonical id to value in LOINC-dictionary units.
        chronological_age: Age in years from the report, or None.

    Returns:
        A score only when the age is present and all nine markers are present
        and usable. Otherwise both score fields are None. ``missing_markers``
        lists absent ids in dictionary order. A present value that the formula
        cannot use is not reported as missing.
    """
    missing = missing_phenoage_markers(markers)
    if chronological_age is None or missing:
        return ConfirmedPanelPhenoAge(
            pheno_age=None,
            age_delta=None,
            missing_markers=missing,
            disclaimer=RESEARCH_DISCLAIMER,
        )
    try:
        result = calculate_canonical_phenoage(
            CanonicalBiomarkers(
                albumin_g_l=markers["albumin"],
                creatinine_mg_dl=markers["creatinine"],
                glucose_mg_dl=markers["glucose"],
                crp_mg_l=markers["crp"],
                lymphocyte_percent=markers["lymphocyte"],
                mcv_fl=markers["mcv"],
                rdw_percent=markers["rdw"],
                alp_u_l=markers["alp"],
                wbc_10e3_per_ul=markers["wbc"],
                age_years=chronological_age,
            )
        )
    except PhenoAgeInputError:
        return ConfirmedPanelPhenoAge(
            pheno_age=None,
            age_delta=None,
            missing_markers=(),
            disclaimer=RESEARCH_DISCLAIMER,
        )
    return ConfirmedPanelPhenoAge(
        pheno_age=result.pheno_age,
        age_delta=result.age_delta,
        missing_markers=(),
        disclaimer=result.disclaimer,
    )


def calculate_canonical_phenoage(markers: CanonicalBiomarkers) -> PhenoAgeResult:
    """Convert dictionary units into Levine units and score them.

    Args:
        markers: Values in the LOINC dictionary canonical units.

    Returns:
        The same result as ``calculate_levine_phenoage`` after conversion.

    Raises:
        PhenoAgeInputError: A converted value cannot be scored.
    """
    return calculate_levine_phenoage(_to_levine_units(markers))


def _to_levine_units(markers: CanonicalBiomarkers) -> LevineBiomarkers:
    """Scale creatinine, glucose, and CRP into the units Table 1 uses."""
    return LevineBiomarkers(
        albumin_g_l=markers.albumin_g_l,
        creatinine_umol_l=_scale(markers.creatinine_mg_dl, _CREATININE_UMOL_PER_MG_DL),
        glucose_mmol_l=_scale(markers.glucose_mg_dl, _GLUCOSE_MMOL_PER_MG_DL),
        crp_mg_dl=_scale(markers.crp_mg_l, _CRP_MG_DL_PER_MG_L),
        lymphocyte_percent=markers.lymphocyte_percent,
        mcv_fl=markers.mcv_fl,
        rdw_percent=markers.rdw_percent,
        alp_u_l=markers.alp_u_l,
        wbc_10e3_per_ul=markers.wbc_10e3_per_ul,
        age_years=markers.age_years,
    )


def _scale(value: float, factor: Decimal) -> float:
    """Multiply a reported number by a dictionary conversion factor."""
    return float(Decimal(str(value)) * factor)


def _require_finite(markers: LevineBiomarkers) -> None:
    """Reject NaN and infinity before the Gompertz transform."""
    values = (
        markers.albumin_g_l,
        markers.creatinine_umol_l,
        markers.glucose_mmol_l,
        markers.crp_mg_dl,
        markers.lymphocyte_percent,
        markers.mcv_fl,
        markers.rdw_percent,
        markers.alp_u_l,
        markers.wbc_10e3_per_ul,
        markers.age_years,
    )
    if not all(math.isfinite(value) for value in values):
        raise PhenoAgeInputError("PhenoAge inputs must be finite")


def _linear_predictor(markers: LevineBiomarkers) -> float:
    """Return xb from Supplementary Table S1."""
    return (
        _INTERCEPT
        + _ALBUMIN_G_L * markers.albumin_g_l
        + _CREATININE_UMOL_L * markers.creatinine_umol_l
        + _GLUCOSE_MMOL_L * markers.glucose_mmol_l
        + _LN_CRP_MG_DL * math.log(markers.crp_mg_dl)
        + _LYMPHOCYTE_PERCENT * markers.lymphocyte_percent
        + _MCV_FL * markers.mcv_fl
        + _RDW_PERCENT * markers.rdw_percent
        + _ALP_U_L * markers.alp_u_l
        + _WBC_10E3_PER_UL * markers.wbc_10e3_per_ul
        + _AGE_YEARS * markers.age_years
    )


def _ten_year_mortality(linear_predictor: float) -> float:
    """Return CDF(120 months) from the supplement methods."""
    hazard = math.exp(linear_predictor) * ((math.exp(_GAMMA * _HORIZON_MONTHS) - 1.0) / _GAMMA)
    return 1.0 - math.exp(-hazard)


def _phenotypic_age(mortality: float) -> float:
    """Invert the univariate Gompertz model into years.

    Raises:
        PhenoAgeInputError: The published transform is undefined.
    """
    if not 0.0 < mortality < 1.0:
        raise PhenoAgeInputError("10-year mortality is outside the open unit interval")
    inner = _PHENO_LN_SCALE * math.log(1.0 - mortality)
    if inner <= 0.0:
        raise PhenoAgeInputError("phenotypic age transform is undefined")
    return _PHENO_INTERCEPT + math.log(inner) / _PHENO_DIVISOR
