"""Process-local extract sessions. Tokens live in RAM; file bytes do not."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID

from app.domain.uploads import ExtractedPanel, ExtractSession, ExtractSessionNotFoundError


class InMemoryExtractSessionStore:
    """TTL map of extract tokens. Safe for a single uvicorn worker."""

    def __init__(
        self,
        ttl_seconds: int,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, ExtractSession] = {}
        self._lock = Lock()
        self._now = now if now is not None else lambda: datetime.now(UTC)

    def put(self, user_id: UUID, panel: ExtractedPanel) -> ExtractSession:
        """Store a panel and return a one-time session.

        Args:
            user_id: Owner of the extract.
            panel: Structured extraction without file bytes.
        """
        session = ExtractSession(
            token=secrets.token_urlsafe(32),
            user_id=user_id,
            panel=panel,
            created_at=self._now(),
        )
        with self._lock:
            self._drop_expired(self._now())
            self._items[session.token] = session
        return session

    def get(self, token: str, user_id: UUID) -> ExtractSession:
        """Return a live session owned by ``user_id``.

        Args:
            token: Opaque extract token from the extract response.
            user_id: Authenticated caller.

        Raises:
            ExtractSessionNotFoundError: Missing, expired, or wrong owner.
        """
        with self._lock:
            session = self._items.get(token)
            if session is None:
                raise ExtractSessionNotFoundError
            if self._now() - session.created_at > self._ttl:
                del self._items[token]
                raise ExtractSessionNotFoundError
            if session.user_id != user_id:
                raise ExtractSessionNotFoundError
            return session

    def pop(self, token: str, user_id: UUID) -> ExtractSession:
        """Return and delete a live session owned by ``user_id``.

        Args:
            token: Opaque extract token.
            user_id: Authenticated caller.
        """
        session = self.get(token, user_id)
        with self._lock:
            self._items.pop(token, None)
        return session

    def clear(self) -> None:
        """Drop every session. Used on process shutdown."""
        with self._lock:
            self._items.clear()

    def _drop_expired(self, now: datetime) -> None:
        """Remove sessions whose TTL has elapsed. Caller holds the lock."""
        expired = [
            token for token, session in self._items.items() if now - session.created_at > self._ttl
        ]
        for token in expired:
            del self._items[token]
