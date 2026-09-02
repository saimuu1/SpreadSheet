// Concurrency + correctness tests for the sharded, bounded rate limiter.
//
//   c++ -std=c++17 -O2 -Wall -Wextra -pthread -I ../include test_sharded.cpp -o /tmp/sh_test
//   /tmp/sh_test
//
#include "sharded_limiter.hpp"
#include "token_bucket.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <vector>

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

using rl::ShardedRateLimiter;

// A limiter modeled exactly on the ORIGINAL backend logic: read a count, then
// (after a gap standing in for the DB round-trip) conditionally write. Each
// load/store is atomic (no UB), but the read-check-write is NOT atomic — this is
// the TOCTOU race the old `SELECT count(*)` … `INSERT` had.
struct NaiveCountThenInsert {
    std::atomic<int> count{0};
    int limit;
    explicit NaiveCountThenInsert(int lim) : limit(lim) {}
    bool allow() {
        int c = count.load(std::memory_order_relaxed);  // like SELECT count(*)
        // A real gap standing in for the DB round-trip. Making it a genuine sleep
        // (not a yield) means the race window is wall-clock wide, so the demo is
        // deterministic instead of dependent on the scheduler.
        std::this_thread::sleep_for(std::chrono::microseconds(5));
        if (c < limit) {
            count.store(c + 1, std::memory_order_relaxed);  // like INSERT
            return true;
        }
        return false;
    }
};

template <typename Fn>
static int run_threads(int num_threads, Fn per_thread) {
    std::atomic<int> total{0};
    std::vector<std::thread> ts;
    ts.reserve(num_threads);
    for (int t = 0; t < num_threads; ++t)
        ts.emplace_back([&] { total.fetch_add(per_thread(), std::memory_order_relaxed); });
    for (auto& th : ts) th.join();
    return total.load();
}

int main() {
    std::printf("sharded limiter tests\n");

    // 1. Single-key correctness (single thread, fixed clock).
    {
        ShardedRateLimiter lim(2, 8);
        int ok = 0;
        for (int i = 0; i < 10; ++i) ok += lim.allow_at(42, /*rate*/ 5, /*burst*/ 3, /*now*/ 0);
        CHECK(ok == 3, "single key: burst=3 enforced, rest rejected");
    }

    // 2. THE RACE, reproduced deterministically. All threads are released from a
    // barrier at once, and the check→write gap is a real sleep, so many threads
    // read the same stale count before any writes land. A correct limiter would
    // grant exactly `limit`; the naive one grants far more.
    {
        NaiveCountThenInsert naive(/*limit*/ 50);
        const int T = 8, per = 200;
        std::atomic<int> arrived{0};
        std::atomic<bool> go{false};
        std::atomic<int> allowed{0};
        std::vector<std::thread> ts;
        for (int t = 0; t < T; ++t) {
            ts.emplace_back([&] {
                arrived.fetch_add(1, std::memory_order_relaxed);
                while (!go.load(std::memory_order_acquire)) { /* start together */ }
                int local = 0;
                for (int i = 0; i < per; ++i)
                    if (naive.allow()) ++local;
                allowed.fetch_add(local, std::memory_order_relaxed);
            });
        }
        while (arrived.load(std::memory_order_relaxed) < T) { /* wait for all ready */ }
        go.store(true, std::memory_order_release);  // release the barrier
        for (auto& th : ts) th.join();
        std::printf("      naive count-then-insert allowed %d (limit was 50)\n", allowed.load());
        CHECK(allowed.load() > 50, "naive limiter OVER-allows under concurrency (TOCTOU race present)");
    }

    // 3. THE FIX, proven: the token bucket is atomic — exactly `burst` pass.
    // All threads consume at the SAME injected time, so no refill occurs; the
    // only tokens available are the initial burst. A correct (atomic) limiter
    // grants EXACTLY burst regardless of interleaving; a racy one would exceed.
    {
        ShardedRateLimiter lim(4, 64);
        const uint64_t key = 0xABCDEF123ull;
        const uint32_t burst = 100;
        int allowed = run_threads(8, [&] {
            int local = 0;
            for (int i = 0; i < 1000; ++i)
                if (lim.allow_at(key, /*rate*/ 1000, burst, /*now*/ 5000)) ++local;
            return local;
        });
        std::printf("      token-bucket granted %d of %d attempts (burst=%u)\n",
                    allowed, 8 * 1000, burst);
        CHECK(allowed == (int)burst,
              "8 threads, fixed clock -> EXACTLY burst granted (atomic, no race)");
    }

    // 4. Memory is bounded: 1000 distinct keys, fixed-capacity table.
    {
        ShardedRateLimiter lim(4, 16);  // capacity 64
        for (uint64_t k = 1; k <= 1000; ++k)
            lim.allow_at(k, /*rate*/ 100, /*burst*/ 10, /*now*/ 1000);
        CHECK(lim.capacity() == 64, "table capacity is fixed at shards*slots = 64");
        CHECK(lim.size() <= lim.capacity(),
              "memory bounded: occupied slots never exceed capacity despite 1000 keys");
    }

    // 5. Many keys hammered concurrently — no crash, each key independently limited.
    {
        ShardedRateLimiter lim(8, 64);
        const uint32_t burst = 20;
        std::atomic<int> overs{0};
        std::vector<std::thread> ts;
        for (int k = 0; k < 32; ++k) {
            ts.emplace_back([&, k] {
                int granted = 0;
                for (int i = 0; i < 500; ++i)
                    if (lim.allow_at(1000 + k, 100, burst, 7000)) ++granted;
                // fixed clock => at most `burst` should ever be granted per key
                if (granted > (int)burst) overs.fetch_add(1, std::memory_order_relaxed);
            });
        }
        for (auto& th : ts) th.join();
        CHECK(overs.load() == 0, "32 keys x concurrent hammering: no key ever exceeds its burst");
    }

    if (g_failures == 0) {
        std::printf("\nALL TESTS PASSED\n");
        return 0;
    }
    std::printf("\n%d TEST(S) FAILED\n", g_failures);
    return 1;
}
