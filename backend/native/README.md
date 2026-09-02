# `ratelimiter` — a lock-free token-bucket rate limiter (C++)

Replaces the backend's original rate limiter, which counted rows in Postgres
(`SELECT count(*) FROM request_logs …`) on every request. That approach had two real
defects:

1. **A TOCTOU race** — the `count` and the `insert` were not atomic, so two concurrent
   requests could both read `9 < 10` and both be allowed. The limit was not actually
   enforced under concurrency.
2. **Unbounded state** — `request_logs` grew forever, so the counting query got slower with
   age, and memory/storage were unbounded.

This module fixes both: an in-process **token-bucket** limiter whose per-key state is a single
64-bit atomic (so a decision is one compare-and-swap, no lock), stored in a **bounded** table.

---

## Semantics: token bucket (not fixed window)

Each key has a bucket that holds up to `burst` tokens and refills at `rate` tokens/second.
A request consumes one token; if none are available it's rejected. This gives a smooth
sustained rate with a controlled burst — unlike a fixed window, which allows `2*limit`
requests across a window boundary.

## The core trick: pack the whole bucket into one atomic word

```
 ┌──────────────────── std::atomic<uint64_t> ────────────────────┐
 │  bits 63..32:  last_refill_ms   │  bits 31..0:  tokens_milli   │
 └───────────────────────────────────────────────────────────────┘
```

- **`tokens_milli`** — tokens in fixed-point ("millitokens", ×1000), so sub-token refill is
  representable **without floats inside the atomic**.
- **`last_refill_ms`** — monotonic milliseconds, relative to process start.

Consuming a token is a single CAS loop:

```
load word
  decode (last_ms, tokens)
  elapsed  = now_ms - last_ms                 # unsigned → wrap-safe delta
  refilled = min(capacity, tokens + elapsed * rate_mt_per_ms)
  if refilled < 1 token: return false          # reject, and DON'T write (no contention)
  CAS word -> (now_ms, refilled - 1 token)     # retry on failure
```

### Deliberate decisions (the interesting bits)
- **1 token/sec == 1 millitoken/ms**, so the refill rate is just `rate_per_sec`. No division
  on the hot path.
- **Reject without writing.** Refill is a pure function of `(now - last)`, so leaving `last`
  in place keeps accrual correct and avoids pointless CAS contention on rejected requests.
- **32-bit ms timestamp** wraps every ~49.7 days; unsigned subtraction keeps the delta correct
  for any real gap under that. (A bucket untouched for >49 days would mis-refill once — it's
  already at capacity by then, so it's harmless.)
- **Memory ordering:** `acquire` load, `acq_rel` on success — enough to publish the new token
  count to the next thread without a full `seq_cst` fence.
- `static_assert(is_always_lock_free)` — proves the 64-bit atomic compiles to a real
  lock-free instruction on the target (true on x86-64 and arm64).

---

## The sharded, bounded table (Phase 2)

`ShardedRateLimiter` holds a **fixed** number of bucket slots, so memory can't grow with the
(unbounded) set of API keys — fixing the original limiter's unbounded `request_logs`.

Concurrency strategy — **lock-free where it's hot, locked where it's rare**:
- **Fast path (no lock):** probe for the key with atomic loads, then consume via the
  lock-free CAS above.
- **Slow path (per-shard striped mutex):** only on a miss — insert, or **CLOCK / second-chance
  evict** a cold slot.
- **Evict-vs-consume safety:** a consumer sets a slot's CLOCK reference bit before consuming;
  eviction only reclaims slots with a *clear* bit, so a hot key is never evicted out from
  under a live consumer. The one residual race (a cold key evicted at the instant a straggler
  consumes it) **fails safe** — at most one extra token is charged to the incoming key; the
  limit is never exceeded.

## Build & test

Header-only, standalone (no Python yet). Needs a C++17 compiler:

```bash
# Phase 1 — single-bucket core
c++ -std=c++17 -O2 -Wall -Wextra -I include tests/test_token_bucket.cpp -o /tmp/tb && /tmp/tb

# Phase 2 — sharded limiter + concurrency stress tests
c++ -std=c++17 -O2 -Wall -Wextra -pthread -I include tests/test_sharded.cpp -o /tmp/sh && /tmp/sh

# Phase 2 — under ThreadSanitizer (must be race-clean AND pass)
c++ -std=c++17 -O1 -g -fsanitize=thread -pthread -I include tests/test_sharded.cpp -o /tmp/sht && /tmp/sht
```

Verified results: the naive count-then-insert over-allows (**~430 vs a limit of 50**), the
token bucket grants **exactly `burst`** under 8 concurrent threads, memory stays bounded across
1000 keys, and **ThreadSanitizer reports zero data races**.

## Roadmap
- **Phase 1 (done):** lock-free single-bucket core + single-threaded correctness tests.
- **Phase 2 (done):** sharded bounded table (striped locks, CLOCK eviction); multi-threaded
  stress test that reproduces the old TOCTOU race and proves this limiter is race-free (clean
  under ThreadSanitizer).
- **Phase 3:** pybind11 binding with `gil_scoped_release`.
- **Phase 4:** wire into FastAPI with a pure-Python fallback; decouple analytics logging.
- **Phase 5:** benchmark (throughput / p99) vs the old DB approach.
