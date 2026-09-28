"""Protocol journal use-cases. No FastAPI and no ORM models."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Protocol
from uuid import UUID

import structlog

from app.domain.protocol import (
    ProtocolDraft,
    ProtocolEntry,
    ProtocolEntryNotFoundError,
    protocol_draft,
)

logger = structlog.get_logger(__name__)


class ProtocolStore(Protocol):
    """Persistence contract for one participant's journal."""

    async def list_for_user(self, user_id: UUID) -> tuple[ProtocolEntry, ...]:
        """Return this participant's rows."""

    async def insert(self, user_id: UUID, draft: ProtocolDraft, *, now: datetime) -> ProtocolEntry:
        """Insert one row."""

    async def replace(
        self,
        user_id: UUID,
        entry_id: UUID,
        draft: ProtocolDraft,
        *,
        now: datetime,
    ) -> ProtocolEntry | None:
        """Replace one owned row, or return None."""

    async def delete(self, user_id: UUID, entry_id: UUID) -> bool:
        """Delete one owned row."""


class ProtocolService:
    """Create, list, replace, and delete journal rows for the signed-in participant."""

    def __init__(
        self,
        store: ProtocolStore,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._store = store
        self._clock = clock or (lambda: datetime.now(UTC))

    async def list_entries(self, user_id: UUID) -> tuple[ProtocolEntry, ...]:
        """Return this participant's journal.

        Args:
            user_id: Authenticated participant.
        """
        return await self._store.list_for_user(user_id)

    async def create_entry(
        self,
        user_id: UUID,
        *,
        kind: str,
        title: str,
        dose: str | None,
        started_on: date,
        ended_on: date | None,
        note: str | None,
    ) -> ProtocolEntry:
        """Store one journal row.

        Args:
            user_id: Authenticated participant.
            kind: Journal type.
            title: Free-text name.
            dose: Optional dose.
            started_on: First day.
            ended_on: Last day, or None.
            note: Optional note.

        Raises:
            ProtocolValidationError: The row cannot be stored.
        """
        draft = protocol_draft(
            kind=kind,
            title=title,
            dose=dose,
            started_on=started_on,
            ended_on=ended_on,
            note=note,
        )
        saved = await self._store.insert(user_id, draft, now=self._clock())
        logger.info("protocol_entry_saved")
        return saved

    async def replace_entry(
        self,
        user_id: UUID,
        entry_id: UUID,
        *,
        kind: str,
        title: str,
        dose: str | None,
        started_on: date,
        ended_on: date | None,
        note: str | None,
    ) -> ProtocolEntry:
        """Replace one owned row.

        Args:
            user_id: Authenticated participant.
            entry_id: Row to replace.
            kind: Journal type.
            title: Free-text name.
            dose: Optional dose.
            started_on: First day.
            ended_on: Last day, or None.
            note: Optional note.

        Raises:
            ProtocolValidationError: The row cannot be stored.
            ProtocolEntryNotFoundError: The id is missing or belongs to someone else.
        """
        draft = protocol_draft(
            kind=kind,
            title=title,
            dose=dose,
            started_on=started_on,
            ended_on=ended_on,
            note=note,
        )
        saved = await self._store.replace(user_id, entry_id, draft, now=self._clock())
        if saved is None:
            raise ProtocolEntryNotFoundError
        logger.info("protocol_entry_replaced")
        return saved

    async def delete_entry(self, user_id: UUID, entry_id: UUID) -> None:
        """Delete one owned row.

        Args:
            user_id: Authenticated participant.
            entry_id: Row to remove.

        Raises:
            ProtocolEntryNotFoundError: The id is missing or belongs to someone else.
        """
        deleted = await self._store.delete(user_id, entry_id)
        if not deleted:
            raise ProtocolEntryNotFoundError
        logger.info("protocol_entry_deleted")
