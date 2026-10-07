"""PhenoAge HTTP surface. The Levine formula lives in the service, not here."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dataset import enforce_public_rate_limit
from app.domain.schemas import PhenoAgeRequest, PhenoAgeResponse
from app.services.phenoage import (
    CanonicalBiomarkers,
    PhenoAgeInputError,
    calculate_canonical_phenoage,
)

router = APIRouter(prefix="/api/v1/phenoage", tags=["phenoage"])


@router.post("", response_model=PhenoAgeResponse)
def score_phenoage(
    body: PhenoAgeRequest,
    _: Annotated[None, Depends(enforce_public_rate_limit)],
) -> PhenoAgeResponse:
    """Score nine biomarkers. Nothing is stored."""
    markers = body.markers
    try:
        result = calculate_canonical_phenoage(
            CanonicalBiomarkers(
                albumin_g_l=markers.albumin,
                creatinine_mg_dl=markers.creatinine,
                glucose_mg_dl=markers.glucose,
                crp_mg_l=markers.crp,
                lymphocyte_percent=markers.lymphocyte,
                mcv_fl=markers.mcv,
                rdw_percent=markers.rdw,
                alp_u_l=markers.alp,
                wbc_10e3_per_ul=markers.wbc,
                age_years=body.chronological_age,
            )
        )
    except PhenoAgeInputError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="PhenoAge inputs are not usable",
        ) from exc
    return PhenoAgeResponse(
        chronological_age=result.chronological_age,
        pheno_age=result.pheno_age,
        age_delta=result.age_delta,
        disclaimer=result.disclaimer,
    )
