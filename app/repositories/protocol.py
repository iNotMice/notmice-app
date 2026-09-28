"""Protocol journal persistence. Rows are keyed by the participant id."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.protocol import ProtocolDraft, ProtocolEntry, ProtocolKindName
from app.repositories.models import ProtocolEntryRow


class ProtocolRepository:
    """Async reads and writes of ``protocol_entries``."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_for_user(self, user_id: UUID) -> tuple[ProtocolEntry, ...]:
        """Return this participant's rows, earliest start first.

        Args:
            user_id: Owner. Other participants are not included.
        """
        result = await self._session.execute(
            select(ProtocolEntryRow)
            .where(ProtocolEntryRow.user_id == user_id)
            .order_by(ProtocolEntryRow.started_on.asc(), ProtocolEntryRow.created_at.asc())
        )
        return tuple(_to_entry(row) for row in result.scalars().all())

    async def insert(self, user_id: UUID, draft: ProtocolDraft, *, now: datetime) -> ProtocolEntry:
        """Insert one row for this participant.

        Args:
            user_id: Owner.
            draft: Checked journal fields.
            now: Timestamp stored as the update time.
        """
        row = ProtocolEntryRow(
            id=uuid4(),
            user_id=user_id,
            kind=draft.kind,
            title=draft.title,
            dose=draft.dose,
            started_on=draft.started_on,
            ended_on=draft.ended_on,
            note=draft.note,
            updated_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_entry(row)

    async def replace(
        self,
        user_id: UUID,
        entry_id: UUID,
        draft: ProtocolDraft,
        *,
        now: datetime,
    ) -> ProtocolEntry | None:
        """Replace one owned row. Another participant's id is left untouched.

        Args:
            user_id: Owner.
            entry_id: Row to replace.
            draft: Checked journal fields.
            now: Timestamp stored as the update time.

        Returns:
            The updated row, or None when this participant does not own that id.
        """
        result = await self._session.execute(
            select(ProtocolEntryRow).where(
                ProtocolEntryRow.id == entry_id,
                ProtocolEntryRow.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None
        row.kind = draft.kind
        row.title = draft.title
        row.dose = draft.dose
        row.started_on = draft.started_on
        row.ended_on = draft.ended_on
        row.note = draft.note
        row.updated_at = now
        await self._session.flush()
        return _to_entry(row)

    async def delete(self, user_id: UUID, entry_id: UUID) -> bool:
        """Delete one owned row.

        Args:
            user_id: Owner.
            entry_id: Row to remove.

        Returns:
            True when a row was deleted.
        """
        outcome = cast(
            CursorResult[Any],
            await self._session.execute(
                delete(ProtocolEntryRow).where(
                    ProtocolEntryRow.id == entry_id,
                    ProtocolEntryRow.user_id == user_id,
                )
            ),
        )
        await self._session.flush()
        return outcome.rowcount == 1


def _to_entry(row: ProtocolEntryRow) -> ProtocolEntry:
    """Map an ORM row to a domain record. The participant id is not copied."""
    return ProtocolEntry(
        id=row.id,
        kind=cast(ProtocolKindName, row.kind),
        title=row.title,
        dose=row.dose,
        started_on=row.started_on,
        ended_on=row.ended_on,
        note=row.note,
    )
