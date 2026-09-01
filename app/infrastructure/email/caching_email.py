"""Email provider wrapper that throttles real IMAP fetches behind a short-lived cache."""
import time
from collections.abc import Callable

from app.domain.entities.email import EmailMessage
from app.domain.ports.email import EmailProvider


class CachedEmailProvider:
    """Implements EmailProvider by caching fetch results for a fixed TTL.

    IMAP round-trips are slow (can block for seconds), so we never hit them more
    often than ``ttl_seconds`` between calls. Falls back to the previous result
    (or the underlying provider's own error handling) on failures while stale
    data is still fresher than nothing.
    """

    def __init__(
        self,
        inner: EmailProvider,
        ttl_seconds: float = 60.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._inner = inner
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._cache: list[EmailMessage] = []
        self._cached_at: float | None = None

    def fetch_recent(
        self,
        days: int = 3,
        limit: int = 15,
        unread_only: bool = True,
    ) -> list[EmailMessage]:
        if self._cached_at is not None and self._clock() - self._cached_at < self._ttl_seconds:
            return self._cache
        try:
            fresh = self._inner.fetch_recent(
                days=days, limit=limit, unread_only=unread_only
            )
            self._cache = fresh
            self._cached_at = self._clock()
            return fresh
        except Exception:  # noqa: BLE001 - fall back to stale cache, never block the loop
            if self._cached_at is not None:
                return self._cache
            return []
