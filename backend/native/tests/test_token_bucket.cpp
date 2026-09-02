// Single-threaded correctness tests for the token-bucket core.
// The clock is injected via try_consume(now_ms), so time is fully deterministic.
//
//   c++ -std=c++17 -O2 -Wall -Wextra -I ../include test_token_bucket.cpp -o /tmp/tb_test
//   /tmp/tb_test
//
#include "token_bucket.hpp"

#include <cmath>
#include <cstdint>
#include <cstdio>

static int g_failures = 0;

#define CHECK(cond, msg)                                             \
    do {                                                             \
        if (cond) {                                                  \
            std::printf("  ok    %s\n", msg);                        \
        } else {                                                     \
            std::printf("  FAIL  %s   (line %d)\n", msg, __LINE__);  \
            ++g_failures;                                            \
        }                                                            \
    } while (0)

using rl::TokenBucket;

int main() {
    std::printf("token_bucket single-threaded tests\n");

    // 1. A fresh bucket is full: exactly `burst` consumes pass at the same instant.
    {
        TokenBucket b(10, 5, 0);  // 10 tok/s, burst 5, start at t=0
        int passed = 0;
        for (int i = 0; i < 5; ++i) passed += b.try_consume(0);
        CHECK(passed == 5, "burst of 5 all pass at t=0");
        CHECK(!b.try_consume(0), "6th request at t=0 is rejected");
    }

    // 2. After draining, one token becomes available after exactly 1/rate seconds.
    {
        TokenBucket b(10, 5, 0);  // 10/s => 1 token every 100 ms
        for (int i = 0; i < 5; ++i) b.try_consume(0);
        CHECK(!b.try_consume(50), "at t=50ms (<100ms) still empty");
        CHECK(b.try_consume(100), "at t=100ms exactly one token has refilled");
        CHECK(!b.try_consume(100), "and only one is available");
    }

    // 3. Fixed-point precision: a fractional token does not round up.
    {
        TokenBucket b(1, 1, 0);  // 1/s, burst 1
        CHECK(b.try_consume(0), "consume the single starting token");
        CHECK(!b.try_consume(0), "now empty");
        CHECK(!b.try_consume(999), "0.999 tokens at t=999ms -> reject");
        CHECK(b.try_consume(1000), "1.000 token at t=1000ms -> allow");
    }

    // 4. Refill is capped at capacity: no unbounded accrual while idle.
    {
        TokenBucket b(10, 5, 0);
        for (int i = 0; i < 5; ++i) b.try_consume(0);
        CHECK(std::fabs(b.tokens_at(10'000) - 5.0) < 1e-9,
              "tokens cap at burst=5 even after 10s idle");
        int passed = 0;
        for (int i = 0; i < 100; ++i) passed += b.try_consume(10'000);
        CHECK(passed == 5, "only burst=5 grantable in one instant after long idle");
    }

    // 5. Steady state grants exactly rate*window over time.
    {
        TokenBucket b(100, 10, 0);  // 100/s, burst 10
        for (int i = 0; i < 10; ++i) b.try_consume(0);  // drain the burst
        int granted = 0;
        for (uint32_t t = 1; t <= 1000; ++t) {
            while (b.try_consume(t)) ++granted;
        }
        CHECK(granted == 100, "steady state grants exactly rate*window = 100 in 1s");
    }

    // 6. The 32-bit millisecond timestamp wraps correctly.
    {
        const uint32_t near_max = 0xFFFFFFC0u;  // 2^32 - 64
        TokenBucket b(10, 5, near_max);
        for (int i = 0; i < 5; ++i) b.try_consume(near_max);
        const uint32_t after = near_max + 100;  // wraps past 2^32 to 36
        CHECK(after < near_max, "sanity: the timestamp actually wrapped");
        CHECK(b.try_consume(after), "one token after 100ms across the uint32 wrap");
    }

    if (g_failures == 0) {
        std::printf("\nALL TESTS PASSED\n");
        return 0;
    }
    std::printf("\n%d TEST(S) FAILED\n", g_failures);
    return 1;
}
