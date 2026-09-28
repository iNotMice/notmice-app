"""RAM holds for a painted frame waiting on a person. The original photo is not stored."""

from __future__ import annotations

import secrets
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from threading import Lock
from uuid import UUID

from app.domain.uploads import ExtractSessionNotFoundError


@dataclass(frozen=True, slots=True)
class RedactionHold:
    """Painted PNG waiting for confirmation. Not the uploaded original."""

    token: str
    user_id: UUID
    document_sha256: str
    payload: bytes
    mime_type: str
    created_at: datetime


class RedactionHoldStore:
    """TTL map of painted frames. Safe for a single uvicorn worker."""

    def __init__(
        self,
        ttl_seconds: int,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._ttl = timedelta(seconds=ttl_seconds)
        self._items: dict[str, RedactionHold] = {}
        self._lock = Lock()
        self._now = now if now is not None else lambda: datetime.now(UTC)

    def put(
        self,
        user_id: UUID,
        *,
        document_sha256: str,
        payload: bytes,
        mime_type: str,
    ) -> str:
        """Store a painted frame and return its token.

        Args:
            user_id: Owner of the upload.
            document_sha256: Hash of the original upload, not of the painted PNG.
            payload: Painted image bytes.
            mime_type: MIME of ``payload``.
        """
        token = secrets.token_urlsafe(32)
        hold = RedactionHold(
            token=token,
            user_id=user_id,
            document_sha256=document_sha256,
            payload=payload,
            mime_type=mime_type,
            created_at=self._now(),
        )
        with self._lock:
            self._drop_expired(self._now())
            self._items[token] = hold
        return token

    def pop(self, token: str, user_id: UUID) -> RedactionHold:
        """Return and delete a live hold owned by ``user_id``.

        Args:
            token: Opaque token from the preview response.
            user_id: Authenticated caller.

        Raises:
            ExtractSessionNotFoundError: Missing, expired, or wrong owner.
        """
        with self._lock:
            self._drop_expired(self._now())
            hold = self._items.get(token)
            if hold is None or hold.user_id != user_id:
                raise ExtractSessionNotFoundError
            del self._items[token]
            return hold

    def clear(self) -> None:
        """Drop every hold. Used on process shutdown."""
        with self._lock:
            self._items.clear()

    def _drop_expired(self, now: datetime) -> None:
        """Remove holds whose TTL has elapsed. Caller holds the lock."""
        expired = [
            token for token, hold in self._items.items() if now - hold.created_at > self._ttl
        ]
        for token in expired:
            del self._items[token]
