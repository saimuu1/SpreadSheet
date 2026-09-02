"""Rate limiting via an in-process token-bucket limiter.

This replaces the original approach — `SELECT count(*)` over `request_logs` on
every request — which had two defects: a **TOCTOU race** (count and insert were
not atomic, so concurrent requests could both pass) and **unbounded growth** (the
log table, and thus the counting query, grew forever).

The new path is an **O(1), in-memory** check with **no DB round-trip**:

  * Preferred backend: the native C++ limiter (``backend/native``) — lock-free
    token buckets packed into one atomic each, in a sharded, bounded table.
  * Fallback: a thread-safe pure-Python token bucket, used automatically if the
    native extension isn't built. A missing native build never breaks the service.

Each key gets two buckets, enforcing the plan's per-minute and per-day caps. A
request must pass BOTH; a request rejected by the second bucket has already spent
a token in the first — a negligible, fail-safe (more restrictive) inaccuracy.
"""

from __future__ import annotations

import threading
import time
import uuid

from fastapi import HTTPException, status

from app.services.plans import Plan

_MASK64 = (1 << 64) - 1


class _PyLimiter:
    """Thread-safe pure-Python token bucket, bounded to `capacity` keys.

    Mirrors the native limiter's semantics: fixed-point millitokens, refill
    recomputed from the last successful consume (so rejects don't mutate state).
    """

    def __init__(self, capacity: int) -> None:
        self._cap = capacity
        self._lock = threading.Lock()
        self._buckets: dict[int, list[int]] = {}  # key -> [tokens_milli, last_ms]

    @staticmethod
    def _now_ms() -> int:
        return time.monotonic_ns() // 1_000_000

    def allow(self, key: int, rate_mt_per_s: int, burst: int) -> bool:
        cap_mt = burst * 1000
        now = self._now_ms()
        with self._lock:
            b = self._buckets.get(key)
            if b is None:
                if len(self._buckets) >= self._cap:
                    self._buckets.pop(next(iter(self._buckets)))  # simple eviction
                b = [cap_mt, now]
                self._buckets[key] = b
            tokens, last = b
            refilled = min(cap_mt, tokens + (now - last) * rate_mt_per_s // 1000)
            if refilled < 1000:
                return False  # reject without writing — refill recomputes next time
            b[0] = refilled - 1000
            b[1] = now
            return True

    def size(self) -> int:
        with self._lock:
            return len(self._buckets)


try:
    from ratelimiter import ShardedRateLimiter as _Native  # type: ignore

    BACKEND = "native (C++)"

    def _make():
        return _Native(num_shards=16, slots_per_shard=4096)  # 65,536 buckets

except ImportError:  # native extension not built — degrade gracefully
    BACKEND = "python (fallback)"

    def _make():
        return _PyLimiter(capacity=65_536)


# One limiter per window; buckets are keyed by API-key hash.
_minute = _make()
_day = _make()


def _key64(api_key_id: str) -> int:
    """Map an API-key id (a UUID) to a 64-bit bucket key."""
    try:
        return uuid.UUID(api_key_id).int & _MASK64
    except (ValueError, AttributeError):
        return hash(api_key_id) & _MASK64


def check_rate_limit(api_key_id: str, plan: Plan) -> None:
    """Raise 429 if the key is over its per-minute or per-day cap. O(1), no DB."""
    key = _key64(api_key_id)

    rpm = plan.requests_per_minute
    # burst == the window's cap; refill smooths it over the window.
    if not _minute.allow(key, round(rpm / 60 * 1000), rpm):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded: {rpm} requests/minute on the {plan.name} plan.",
            headers={"Retry-After": "60"},
        )

    rpd = plan.requests_per_day
    if not _day.allow(key, round(rpd / 86_400 * 1000), rpd):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily quota exceeded: {rpd} requests/day on the {plan.name} plan.",
            headers={"Retry-After": "3600"},
        )
