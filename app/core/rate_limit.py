"""In-process sliding-window rate limit keyed by client address."""

from __future__ import annotations

import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Outcome of one rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class SlidingWindowRateLimiter:
    """Count hits per key inside a rolling window.

    The window lives in this process. Several API workers do not share counters.
    """

    def __init__(
        self,
        *,
        limit: int,
        window_seconds: int,
        now: Callable[[], float] | None = None,
    ) -> None:
        if limit < 1:
            raise ValueError("limit must be positive")
        if window_seconds < 1:
            raise ValueError("window_seconds must be positive")
        self.limit = limit
        self.window_seconds = window_seconds
        self._now = now if now is not None else time.monotonic
        self._events: dict[str, deque[float]] = {}

    async def hit(self, key: str) -> RateLimitDecision:
        """Record one hit for ``key`` or refuse it when the window is full.

        Args:
            key: Caller identity, typically an IP address.
        """
        now = self._now()
        self._forget_expired(now)
        window_start = now - self.window_seconds
        bucket = self._events.get(key)
        if bucket is None:
            bucket = deque()
            self._events[key] = bucket
        while bucket and bucket[0] <= window_start:
            bucket.popleft()
        if not bucket:
            self._events.pop(key, None)
            bucket = deque()
            self._events[key] = bucket
        if len(bucket) >= self.limit:
            retry_after = int(bucket[0] + self.window_seconds - now)
            if retry_after < 1:
                retry_after = 1
            return RateLimitDecision(
                allowed=False,
                limit=self.limit,
                remaining=0,
                retry_after_seconds=retry_after,
            )
        bucket.append(now)
        return RateLimitDecision(
            allowed=True,
            limit=self.limit,
            remaining=self.limit - len(bucket),
            retry_after_seconds=0,
        )

    def _forget_expired(self, now: float) -> None:
        """Drop keys whose newest hit is already outside the window.

        A refusal keeps its bucket, because those timestamps are still inside the window.
        """
        window_start = now - self.window_seconds
        stale = [
            key for key, bucket in self._events.items() if not bucket or bucket[-1] <= window_start
        ]
        for key in stale:
            del self._events[key]


def resolve_client_key(
    *,
    real_ip: str | None,
    client_host: str | None,
    trust_proxy: bool,
) -> str:
    """Choose the address that owns a rate-limit bucket.

    Only ``X-Real-IP`` is honored, and only when the process sits behind the
    project proxy that overwrites that header. ``X-Forwarded-For`` is ignored
    so a caller cannot pick a fresh bucket by spoofing the forwarded list.

    Args:
        real_ip: Value of the X-Real-IP header, if any.
        client_host: Direct peer address from the ASGI connection.
        trust_proxy: When False, the direct peer is always used.
    """
    if trust_proxy and real_ip:
        candidate = real_ip.split(",")[0].strip()
        if candidate:
            return candidate
    if client_host:
        return client_host
    return "unknown"
