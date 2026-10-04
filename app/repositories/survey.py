"""Persistence for the participant-owned optional survey profile."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.survey import Activity, Alcohol, ParticipantProfile, SexAtBirth, Smoking
from app.repositories.models import ParticipantProfileRow, ProfileCondition, User


class SurveyRepository:
    """Read and replace one participant's controlled profile answers."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_profile(self, user_id: UUID) -> ParticipantProfile | None:
        """Load only the authenticated owner's profile."""
        result = await self._session.execute(
            select(User)
            .options(
                selectinload(User.participant_profile),
                selectinload(User.profile_conditions),
            )
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if user is None or user.participant_profile is None:
            return None
        row = user.participant_profile
        return ParticipantProfile(
            sex_at_birth=cast(SexAtBirth | None, row.sex_at_birth),
            year_of_birth=row.year_of_birth,
            country=row.country,
            height_cm=row.height_cm,
            weight_kg=row.weight_kg,
            smoking=cast(Smoking | None, row.smoking),
            alcohol=cast(Alcohol | None, row.alcohol),
            activity=cast(Activity | None, row.activity),
            conditions=tuple(sorted(condition.code for condition in user.profile_conditions)),
            updated_at=row.updated_at,
        )

    async def save_profile(
        self, user_id: UUID, profile: ParticipantProfile
    ) -> ParticipantProfile | None:
        """Insert or replace the owner's profile and its controlled conditions."""
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user is None:
            return None

        now = datetime.now(UTC)
        row_result = await self._session.execute(
            select(ParticipantProfileRow).where(ParticipantProfileRow.user_id == user_id)
        )
        row = row_result.scalar_one_or_none()
        if row is None:
            row = ParticipantProfileRow(id=uuid4(), user_id=user_id)
            self._session.add(row)
        row.sex_at_birth = profile.sex_at_birth
        row.year_of_birth = profile.year_of_birth
        row.country = profile.country
        row.height_cm = profile.height_cm
        row.weight_kg = profile.weight_kg
        row.smoking = profile.smoking
        row.alcohol = profile.alcohol
        row.activity = profile.activity
        row.updated_at = now

        await self._session.execute(
            delete(ProfileCondition).where(ProfileCondition.user_id == user_id)
        )
        self._session.add_all(
            ProfileCondition(id=uuid4(), user_id=user_id, code=code) for code in profile.conditions
        )
        await self._session.flush()
        return ParticipantProfile(
            sex_at_birth=row.sex_at_birth,
            year_of_birth=row.year_of_birth,
            country=row.country,
            height_cm=row.height_cm,
            weight_kg=row.weight_kg,
            smoking=row.smoking,
            alcohol=row.alcohol,
            activity=row.activity,
            conditions=profile.conditions,
            updated_at=row.updated_at,
        )

    async def delete_profile(self, user_id: UUID) -> bool:
        """Delete the owner's profile and conditions; return whether it existed."""
        existing = await self._session.execute(
            select(ParticipantProfileRow.id).where(ParticipantProfileRow.user_id == user_id)
        )
        profile_id = existing.scalar_one_or_none()
        if profile_id is None:
            return False
        await self._session.execute(
            delete(ProfileCondition).where(ProfileCondition.user_id == user_id)
        )
        await self._session.execute(
            delete(ParticipantProfileRow).where(ParticipantProfileRow.user_id == user_id)
        )
        await self._session.flush()
        return True
