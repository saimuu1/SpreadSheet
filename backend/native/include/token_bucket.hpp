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
// The consume logic lives in a free function (`detail::try_consume_word`) so it
// can operate on a bucket owned by a class (TokenBucket) or on a slot inside the
// sharded table (see sharded_limiter.hpp) — one implementation, one place to be
// correct. See README.md for the design rationale.
//
#include <atomic>
#include <chrono>
#include <cstdint>

namespace rl {
namespace detail {

inline constexpr uint32_t ONE_TOKEN_MT = 1000u;  // one token == 1000 millitokens

inline uint64_t pack(uint32_t ts, uint32_t tokens_mt) {
    return (uint64_t(ts) << 32) | uint64_t(tokens_mt);
}
inline uint32_t ts_of(uint64_t w) { return uint32_t(w >> 32); }
inline uint32_t tok_of(uint64_t w) { return uint32_t(w & 0xffffffffu); }

// Lock-free consume of one token from a packed bucket word.
// Returns true iff a token was available (and consumed).
inline bool try_consume_word(std::atomic<uint64_t>& word, uint32_t now_ms,
                             uint32_t refill_mt_per_ms, uint32_t capacity_mt) {
    uint64_t old = word.load(std::memory_order_acquire);
    for (;;) {
        const uint32_t last   = ts_of(old);
        const uint32_t tokens = tok_of(old);

        // Unsigned subtraction gives the correct delta even across the 32-bit
        // wrap, as long as the true gap is < ~49.7 days.
        const uint32_t elapsed = now_ms - last;

        uint64_t refilled =
            uint64_t(tokens) + uint64_t(elapsed) * refill_mt_per_ms;
        if (refilled > capacity_mt) refilled = capacity_mt;

        if (refilled < ONE_TOKEN_MT) {
            // Not enough for a whole token. Do NOT write: refill is a pure
            // function of (now - last), so leaving last in place keeps accrual
            // correct and avoids CAS contention on rejected requests.
            return false;
        }

        const uint64_t next = pack(now_ms, uint32_t(refilled - ONE_TOKEN_MT));
        if (word.compare_exchange_weak(old, next, std::memory_order_acq_rel,
                                       std::memory_order_acquire)) {
            return true;
        }
        // CAS failed: another thread advanced the word; `old` was refreshed by
        // compare_exchange_weak — retry.
    }
}

// Non-consuming: whole-token count if the word were refilled to now_ms.
inline double tokens_in_word(const std::atomic<uint64_t>& word, uint32_t now_ms,
                             uint32_t refill_mt_per_ms, uint32_t capacity_mt) {
    const uint64_t w = word.load(std::memory_order_acquire);
    const uint32_t elapsed = now_ms - ts_of(w);
    uint64_t refilled =
        uint64_t(tok_of(w)) + uint64_t(elapsed) * refill_mt_per_ms;
    if (refilled > capacity_mt) refilled = capacity_mt;
    return double(refilled) / double(ONE_TOKEN_MT);
}

static_assert(std::atomic<uint64_t>::is_always_lock_free,
              "need lock-free 64-bit atomics for a lock-free token bucket");

}  // namespace detail

// A single standalone bucket (used by the Phase 1 tests and as documentation of
// the semantics). The sharded table does not use this class — it applies
// detail::try_consume_word directly to each slot's atomic word.
class TokenBucket {
public:
    TokenBucket(uint32_t rate_per_sec, uint32_t burst, uint32_t now_ms)
        : capacity_mt_(burst * detail::ONE_TOKEN_MT),
          // 1 token/sec == 1000 millitokens / 1000 ms == 1 millitoken/ms.
          refill_mt_per_ms_(rate_per_sec),
          word_(detail::pack(now_ms, burst * detail::ONE_TOKEN_MT)) {}

    TokenBucket(const TokenBucket&) = delete;
    TokenBucket& operator=(const TokenBucket&) = delete;

    bool try_consume(uint32_t now_ms) {
        return detail::try_consume_word(word_, now_ms, refill_mt_per_ms_, capacity_mt_);
    }
    bool allow() { return try_consume(now_ms()); }
    double tokens_at(uint32_t now_ms) const {
        return detail::tokens_in_word(word_, now_ms, refill_mt_per_ms_, capacity_mt_);
    }

    static uint32_t now_ms() {
        using namespace std::chrono;
        static const steady_clock::time_point start = steady_clock::now();
        return uint32_t(
            duration_cast<milliseconds>(steady_clock::now() - start).count());
    }

private:
    const uint32_t capacity_mt_;
    const uint32_t refill_mt_per_ms_;
    std::atomic<uint64_t> word_;
};

}  // namespace rl
