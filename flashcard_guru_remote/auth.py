"""Token generation, constant-time comparison, and brute-force rate limiting."""
from __future__ import annotations

import hmac
import secrets
import time
from collections import defaultdict


def generate_token() -> str:
    """Return a 128-bit random hex token (32 chars)."""
    return secrets.token_hex(16)


def constant_time_equals(a: str, b: str) -> bool:
    """Compare two tokens without leaking length / mismatch position via timing."""
    return hmac.compare_digest(a, b)


class FailureTracker:
    """Per-remote sliding-window counter of authentication failures.

    A remote that exceeds `max_failures` within `window_seconds` is considered
    banned until the window slides past the early failures.
    """

    def __init__(self, max_failures: int = 3, window_seconds: int = 120):
        self._failures: dict[str, list[float]] = defaultdict(list)
        self._max = max_failures
        self._window = window_seconds

    def record_failure(self, remote: str) -> None:
        now = time.monotonic()
        self._failures[remote].append(now)
        self._prune(remote, now)

    def is_banned(self, remote: str) -> bool:
        now = time.monotonic()
        self._prune(remote, now)
        return len(self._failures[remote]) >= self._max

    def reset(self, remote: str) -> None:
        self._failures.pop(remote, None)

    def _prune(self, remote: str, now: float) -> None:
        cutoff = now - self._window
        self._failures[remote] = [t for t in self._failures[remote] if t > cutoff]
