"""Participant survey use-cases. Collection remains gated until legal approval."""

from __future__ import annotations

from uuid import UUID

from app.domain.consents import (
    HEALTH_DATA,
    HEALTH_DATA_VERSION,
    PARTICIPANT_PROFILE,
    PARTICIPANT_PROFILE_VERSION,
    RESEARCH_REUSE_VERSION,
)
from app.domain.survey import (
    ACTIVITY,
    ALCOHOL,
    COUNTRY_CODES,
    PROFILE_CONDITION_CODES,
    PROFILE_GOAL_CODES,
    SEX_AT_BIRTH,
    SMOKING,
    ParticipantProfile,
    SurveyCatalog,
)
from app.repositories.survey import SurveyRepository


class SurveyUnavailableError(RuntimeError):
    """Survey collection is disabled or its approved consent version is missing."""


class SurveyConsentRequiredError(RuntimeError):
    """The participant has not granted the current required profile consents."""


class SurveyService:
    """Owner-scoped survey access, gated by feature state and explicit consent."""

    def __init__(self, repository: SurveyRepository, *, enabled: bool) -> None:
        self._repository = repository
        self._enabled = enabled

    @property
    def catalog(self) -> SurveyCatalog:
        """Return the public controlled vocabulary and rollout state."""
        version = PARTICIPANT_PROFILE_VERSION
        return SurveyCatalog(
            enabled=self._enabled and version is not None,
            health_data_consent_version=HEALTH_DATA_VERSION,
            research_reuse_consent_version=RESEARCH_REUSE_VERSION,
            profile_consent_version=version,
            countries=COUNTRY_CODES,
            sex_at_birth=SEX_AT_BIRTH,
            smoking=SMOKING,
            alcohol=ALCOHOL,
            activity=ACTIVITY,
            conditions=tuple(sorted(PROFILE_CONDITION_CODES)),
            goals=tuple(sorted(PROFILE_GOAL_CODES)),
        )

    async def get_profile(
        self,
        user_id: UUID,
        *,
        granted_consents: frozenset[tuple[str, str]],
    ) -> ParticipantProfile | None:
        """Return the current owner's profile when collection is enabled and consented."""
        self._require_access(granted_consents)
        return await self._repository.get_profile(user_id)

    async def save_profile(
        self,
        user_id: UUID,
        profile: ParticipantProfile,
        *,
        granted_consents: frozenset[tuple[str, str]],
    ) -> ParticipantProfile:
        """Save the current owner's controlled profile."""
        self._require_access(granted_consents)
        saved = await self._repository.save_profile(user_id, profile)
        if saved is None:
            raise SurveyUnavailableError("The participant account no longer exists")
        return saved

    async def delete_profile(
        self,
        user_id: UUID,
    ) -> bool:
        """Delete the current owner's profile without affecting other account data."""
        return await self._repository.delete_profile(user_id)

    def _require_access(self, granted_consents: frozenset[tuple[str, str]]) -> None:
        """Refuse all collection until legal version and participant consents are active."""
        version = PARTICIPANT_PROFILE_VERSION
        if not self._enabled or version is None:
            raise SurveyUnavailableError
        required = {
            (HEALTH_DATA, HEALTH_DATA_VERSION),
            (PARTICIPANT_PROFILE, version),
        }
        if not required.issubset(granted_consents):
            raise SurveyConsentRequiredError
