// Raw throughput benchmark for the sharded limiter (no Python overhead).
//
//   c++ -std=c++17 -O3 -DNDEBUG -pthread -I ../include bench.cpp -o /tmp/rl_bench
//   /tmp/rl_bench
//
#include "sharded_limiter.hpp"

#include <atomic>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <thread>
#include <vector>

using rl::ShardedRateLimiter;
using Clock = std::chrono::steady_clock;

static long work(ShardedRateLimiter& lim, uint64_t base, long iters) {
    long ok = 0;
    for (long i = 0; i < iters; ++i)
        ok += lim.allow(base + (uint64_t(i) & 1023), /*rate_mt_per_s*/ 100000, /*burst*/ 1000);
    return ok;
}

int main() {
    ShardedRateLimiter lim(16, 4096);
    work(lim, 1, 1'000'000);  // warm up

    {
        const long N = 20'000'000;
        auto t0 = Clock::now();
        volatile long ok = work(lim, 1000, N);
        (void)ok;
        double s = std::chrono::duration<double>(Clock::now() - t0).count();
        std::printf("1 thread : %6.1f M ops/s   (%5.1f ns/op)\n", N / s / 1e6, s / N * 1e9);
    }

    for (int T : {2, 4, 8}) {
        const long per = 5'000'000;
        std::vector<std::thread> ts;
        auto t0 = Clock::now();
        for (int t = 0; t < T; ++t)
            ts.emplace_back([&, t] { work(lim, 1000ull + uint64_t(t) * 100000, per); });
        for (auto& th : ts) th.join();
        double s = std::chrono::duration<double>(Clock::now() - t0).count();
        long ops = long(T) * per;
        std::printf("%d threads: %6.1f M ops/s   (%5.1f ns/op)\n", T, ops / s / 1e6, s / ops * 1e9);
    }
    return 0;
}
