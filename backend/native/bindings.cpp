// pybind11 binding: exposes the C++ ShardedRateLimiter to Python as `ratelimiter`.
//
// GIL note (a profiling result worth keeping). The obvious move is to
// `py::gil_scoped_release` around each call. Measured, it isn't worth it: a
// consume is only ~20 ns, so the release/acquire costs more than the work, and —
// the key point — CPU-bound multithreading from CPython is GIL-limited either
// way. In benchmarks, 8 Python threads were slower than 1 whether or not the GIL
// was released (the GIL handoff dominates a loop this tight). So we HOLD the GIL:
// simplest, marginally faster single-threaded, and it makes each call atomic wrt
// Python. The lock-free core's real parallelism shows up in native / free-threaded
// use (bench.cpp: ~200 M ops/s across 8 threads). From the FastAPI backend the win
// isn't Python-thread scaling — it's that each check is ~130 ns with ZERO DB
// round-trips, versus the old ~3 Supabase queries per request.
#include <pybind11/pybind11.h>

#include <cstdint>

#include "sharded_limiter.hpp"

namespace py = pybind11;
using rl::ShardedRateLimiter;

PYBIND11_MODULE(ratelimiter, m) {
    m.doc() = "Lock-free token-bucket rate limiter (C++).";

    py::class_<ShardedRateLimiter>(m, "ShardedRateLimiter")
        .def(py::init<size_t, size_t>(), py::arg("num_shards") = 16,
             py::arg("slots_per_shard") = 1024,
             "Create a limiter with num_shards * slots_per_shard total buckets.")
        .def(
            "allow",
            [](ShardedRateLimiter& self, uint64_t key, uint32_t rate_mt_per_s,
               uint32_t burst) {
                // GIL held on purpose — see module comment (releasing it around a
                // ~20 ns op doesn't help; CPython is GIL-bound here either way).
                return self.allow(key, rate_mt_per_s, burst);
            },
            py::arg("key"), py::arg("rate_mt_per_s"), py::arg("burst"),
            "Consume one token for `key`; returns True if allowed.")
        .def(
            "allow_at",
            [](ShardedRateLimiter& self, uint64_t key, uint32_t rate_mt_per_s,
               uint32_t burst, uint32_t now_ms) {
                return self.allow_at(key, rate_mt_per_s, burst, now_ms);
            },
            py::arg("key"), py::arg("rate_mt_per_s"), py::arg("burst"),
            py::arg("now_ms"), "allow() with an injected clock (for tests/benchmarks).")
        .def("size", &ShardedRateLimiter::size, "Number of occupied buckets.")
        .def("capacity", &ShardedRateLimiter::capacity,
             "Total bucket capacity (fixed).");
}
