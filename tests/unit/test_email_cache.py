"""Tests for the CachedEmailProvider throttling wrapper."""

from app.domain.entities.email import EmailMessage
from app.infrastructure.email.caching_email import CachedEmailProvider


class CounterEmailProvider:
    def __init__(self, messages, fail=False) -> None:
        self.messages = messages
        self.calls = 0
        self.fail = fail

    def fetch_recent(self, days=3, limit=15, unread_only=True):
        self.calls += 1
        if self.fail:
            raise ConnectionError("imap down")
        return self.messages[:limit]


def _msg(uid):
    return EmailMessage(uid=uid, subject="sub", sender="a@b.c", date="", snippet="")


def test_caches_within_ttl():
    inner = CounterEmailProvider([_msg("1")])
    clock = iter([0.0, 1.0, 2.0])
    provider = CachedEmailProvider(inner, ttl_seconds=60.0, clock=lambda: next(clock))
    assert provider.fetch_recent() == [_msg("1")]
    assert provider.fetch_recent() == [_msg("1")]
    assert inner.calls == 1  # second call served from cache


def test_refreshes_after_ttl():
    inner = CounterEmailProvider([_msg("1")])
    times = iter([0.0, 61.0, 62.0])
    provider = CachedEmailProvider(inner, ttl_seconds=60.0, clock=lambda: next(times))
    provider.fetch_recent()
    provider.fetch_recent()
    assert inner.calls == 2


def test_returns_stale_cache_on_failure():
    inner = CounterEmailProvider([_msg("1")])
    times = iter([0.0, 61.0])
    provider = CachedEmailProvider(inner, ttl_seconds=60.0, clock=lambda: next(times))
    provider.fetch_recent()
    inner.fail = True
    assert provider.fetch_recent() == [_msg("1")]  # cached data wins over an error
    assert inner.calls == 2


def test_never_hits_inner_when_unconfigured_returns_empty():
    inner = CounterEmailProvider([])
    clock = iter([0.0, 61.0])
    provider = CachedEmailProvider(inner, ttl_seconds=60.0, clock=lambda: next(clock))
    assert provider.fetch_recent() == []
    assert inner.calls == 1
