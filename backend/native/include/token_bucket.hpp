#pragma once
//
// A lock-free token-bucket rate limiter.
//
// The entire mutable state of a bucket is packed into ONE 64-bit atomic, so
// consuming a token is a single compare-and-swap — there is no per-bucket lock:
//
//   bits 63..32 : last_refill_ms  (monotonic ms, wraps ~49.7 days)
//   bits 31..0  : tokens_milli    (fixed-point, 1 token == 1000 millitokens)
//
// Fixed-point tokens let sub-token refill be represented without floats inside
// the atomic word. See README.md for the design rationale.
//
#include <atomic>
#include <chrono>
#include <cstdint>

namespace rl {

class TokenBucket {
public:
    // rate_per_sec : sustained tokens granted per second.
    // burst        : maximum tokens that can accumulate (bucket capacity).
    // now_ms       : current monotonic time; the bucket starts full at now_ms.
    TokenBucket(uint32_t rate_per_sec, uint32_t burst, uint32_t now_ms)
        : capacity_mt_(burst * ONE_TOKEN_MT),
          // 1 token/sec == 1000 millitokens / 1000 ms == 1 millitoken/ms.
          refill_mt_per_ms_(rate_per_sec),
          word_(pack(now_ms, burst * ONE_TOKEN_MT)) {}

    TokenBucket(const TokenBucket&) = delete;
    TokenBucket& operator=(const TokenBucket&) = delete;

    // Testable core: try to consume one token given an injected clock.
    // Returns true iff a token was available (and was consumed).
    bool try_consume(uint32_t now_ms) {
        uint64_t old = word_.load(std::memory_order_acquire);
        for (;;) {
            const uint32_t last   = ts_of(old);
            const uint32_t tokens = tok_of(old);

            // Unsigned subtraction gives the correct delta even across the
            // 32-bit wrap, as long as the true gap is < ~49.7 days.
            const uint32_t elapsed = now_ms - last;

            uint64_t refilled =
                uint64_t(tokens) + uint64_t(elapsed) * refill_mt_per_ms_;
            if (refilled > capacity_mt_) refilled = capacity_mt_;

            if (refilled < ONE_TOKEN_MT) {
                // Not enough for a whole token. Do NOT write: refill is a pure
                // function of (now - last), so leaving last in place keeps the
                // accrual correct and avoids CAS contention on rejects.
                return false;
            }

            const uint64_t next =
                pack(now_ms, uint32_t(refilled - ONE_TOKEN_MT));
            if (word_.compare_exchange_weak(old, next,
                                            std::memory_order_acq_rel,
                                            std::memory_order_acquire)) {
                return true;
            }
            // CAS failed: another thread advanced the word; `old` now holds the
            // fresh value (compare_exchange_weak refreshed it) — retry.
        }
    }

    // Production entry point: reads the real monotonic clock.
    bool allow() { return try_consume(now_ms()); }

    // Non-consuming introspection (for tests): whole-token count if refilled to now_ms.
    double tokens_at(uint32_t now_ms) const {
        const uint64_t w = word_.load(std::memory_order_acquire);
        const uint32_t elapsed = now_ms - ts_of(w);
        uint64_t refilled =
            uint64_t(tok_of(w)) + uint64_t(elapsed) * refill_mt_per_ms_;
        if (refilled > capacity_mt_) refilled = capacity_mt_;
        return double(refilled) / double(ONE_TOKEN_MT);
    }

    // Monotonic milliseconds since first call (process-relative), truncated to 32 bits.
    static uint32_t now_ms() {
        using namespace std::chrono;
        static const steady_clock::time_point start = steady_clock::now();
        return uint32_t(
            duration_cast<milliseconds>(steady_clock::now() - start).count());
    }

private:
    static constexpr uint32_t ONE_TOKEN_MT = 1000u;

    static uint64_t pack(uint32_t ts, uint32_t tokens_mt) {
        return (uint64_t(ts) << 32) | uint64_t(tokens_mt);
    }
    static uint32_t ts_of(uint64_t w) { return uint32_t(w >> 32); }
    static uint32_t tok_of(uint64_t w) { return uint32_t(w & 0xffffffffu); }

    const uint32_t capacity_mt_;
    const uint32_t refill_mt_per_ms_;
    std::atomic<uint64_t> word_;

    static_assert(std::atomic<uint64_t>::is_always_lock_free,
                  "need lock-free 64-bit atomics for a lock-free token bucket");
};

}  // namespace rl
