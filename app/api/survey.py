"""Participant-owned profile survey API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.accounts import get_current_user
from app.core.deps import get_account_service, get_survey_service
from app.domain.accounts import ConsentRecord, UserRecord
from app.domain.pii import PIIValidationError, reject_pii
from app.domain.schemas import ParticipantProfileView, SurveyCatalogView
from app.domain.survey import ParticipantProfile, ParticipantProfileInput, profile_from_input
from app.services.accounts import AccountService
from app.services.survey import (
    SurveyConsentRequiredError,
    SurveyService,
    SurveyUnavailableError,
)

router = APIRouter(tags=["participant survey"])


def _granted_consents(rows: tuple[ConsentRecord, ...]) -> frozenset[tuple[str, str]]:
    """Return active consent/version pairs without withdrawal timestamps."""
    return frozenset(
        (row.consent_type, row.text_version) for row in rows if row.withdrawn_at is None
    )


def _profile_view(profile: ParticipantProfile | None) -> ParticipantProfileView:
    """Map the persistence-neutral profile to its owner-only response."""
    if profile is None:
        return ParticipantProfileView(
            sex_at_birth=None,
            year_of_birth=None,
            country=None,
            height_cm=None,
            weight_kg=None,
            smoking=None,
            alcohol=None,
            activity=None,
            conditions=[],
            updated_at=None,
        )
    return ParticipantProfileView(
        sex_at_birth=profile.sex_at_birth,
        year_of_birth=profile.year_of_birth,
        country=profile.country,
        height_cm=profile.height_cm,
        weight_kg=profile.weight_kg,
        smoking=profile.smoking,
        alcohol=profile.alcohol,
        activity=profile.activity,
        conditions=list(profile.conditions),
        updated_at=profile.updated_at,
    )


@router.get("/api/v1/survey/catalog", response_model=SurveyCatalogView)
async def read_survey_catalog(
    survey: Annotated[SurveyService, Depends(get_survey_service)],
) -> SurveyCatalogView:
    """Return fixed survey choices and whether profile collection is legally enabled."""
    catalog = survey.catalog
    return SurveyCatalogView(
        enabled=catalog.enabled,
        health_data_consent_version=catalog.health_data_consent_version,
        research_reuse_consent_version=catalog.research_reuse_consent_version,
        profile_consent_version=catalog.profile_consent_version,
        public_sharing_consent_version=catalog.public_sharing_consent_version,
        country_code_pattern=r"^[A-Z]{2}$",
        countries=list(catalog.countries),
        sex_at_birth=list(catalog.sex_at_birth),
        smoking=list(catalog.smoking),
        alcohol=list(catalog.alcohol),
        activity=list(catalog.activity),
        conditions=list(catalog.conditions),
        goals=list(catalog.goals),
    )


@router.get("/api/v1/accounts/me/profile", response_model=ParticipantProfileView)
async def read_profile(
    current: Annotated[UserRecord, Depends(get_current_user)],
    accounts: Annotated[AccountService, Depends(get_account_service)],
    survey: Annotated[SurveyService, Depends(get_survey_service)],
) -> ParticipantProfileView:
    """Return the authenticated participant's own profile only."""
    consents = _granted_consents(await accounts.list_consents(current.id))
    try:
        return _profile_view(await survey.get_profile(current.id, granted_consents=consents))
    except SurveyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Participant survey collection is not enabled",
        ) from exc
    except SurveyConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current participant profile consent is required",
        ) from exc


@router.put("/api/v1/accounts/me/profile", response_model=ParticipantProfileView)
async def update_profile(
    payload: ParticipantProfileInput,
    current: Annotated[UserRecord, Depends(get_current_user)],
    accounts: Annotated[AccountService, Depends(get_account_service)],
    survey: Annotated[SurveyService, Depends(get_survey_service)],
) -> ParticipantProfileView:
    """Replace the authenticated participant's controlled profile answers."""
    try:
        reject_pii(payload.model_dump(mode="json"))
    except PIIValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Profile contains unsupported personal text",
        ) from exc
    consents = _granted_consents(await accounts.list_consents(current.id))
    try:
        saved = await survey.save_profile(
            current.id,
            profile_from_input(payload),
            granted_consents=consents,
        )
    except SurveyUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Participant survey collection is not enabled",
        ) from exc
    except SurveyConsentRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Current participant profile consent is required",
        ) from exc
    return _profile_view(saved)


@router.delete("/api/v1/accounts/me/profile", status_code=status.HTTP_204_NO_CONTENT)
async def delete_profile(
    current: Annotated[UserRecord, Depends(get_current_user)],
    survey: Annotated[SurveyService, Depends(get_survey_service)],
) -> Response:
    """Delete only the authenticated participant's optional profile answers."""
    await survey.delete_profile(current.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
