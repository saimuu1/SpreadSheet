#pragma once
//
// ShardedRateLimiter — a bounded, concurrent table of token buckets.
//
// Keys (hashed API keys) are unbounded, but memory must not be. So buckets live
// in a FIXED number of slots; when the table is full a new key evicts a cold one
// (CLOCK / second-chance). This fixes the original limiter's unbounded growth.
//
// Concurrency strategy: "lock-free where it's hot, locked where it's rare."
//   * FAST PATH (no lock): probe for an existing bucket with atomic loads, then
//     consume a token with the lock-free CAS from token_bucket.hpp.
//   * SLOW PATH (striped per-shard mutex): only on a miss — insert the key, or
//     CLOCK-evict a cold slot to make room. Rare relative to consumes.
//
// The evict-vs-consume interaction is made safe by CLOCK: a consumer sets a
// slot's reference bit before consuming, and eviction only reclaims slots whose
// reference bit is clear — so an actively-used (hot) key is never evicted out
// from under a concurrent consumer. The only residual race (a cold key being
// evicted at the exact instant a straggler consumes it) fails SAFE: at worst one
// token is charged to the incoming key, never allowing the limit to be exceeded.
//
#include <cstddef>
#include <cstdint>
#include <mutex>
#include <vector>

#include "token_bucket.hpp"

namespace rl {

class ShardedRateLimiter {
public:
    // Total capacity is num_shards * slots_per_shard buckets (fixed).
    ShardedRateLimiter(size_t num_shards, size_t slots_per_shard)
        : shards_(num_shards) {
        for (auto& s : shards_) s.slots = std::vector<Slot>(slots_per_shard);
    }

    // Consume one token for `key`, using the real monotonic clock.
    // rate_mt_per_s is the refill rate in millitokens/second (so fractional
    // token rates like 10/min are exact); burst is the bucket capacity in tokens.
    bool allow(uint64_t key, uint32_t rate_mt_per_s, uint32_t burst) {
        return allow_at(key, rate_mt_per_s, burst, TokenBucket::now_ms());
    }

    // Same, with an injected clock — the deterministic hook the tests drive.
    bool allow_at(uint64_t key, uint32_t rate_mt_per_s, uint32_t burst,
                  uint32_t now_ms) {
        key = normalize(key);
        const uint32_t rate = rate_mt_per_s;                  // millitokens/sec
        const uint32_t cap  = burst * detail::ONE_TOKEN_MT;

        Shard& sh = shards_[mix(key ^ SHARD_SALT) % shards_.size()];
        const size_t n = sh.slots.size();
        const size_t home = size_t(mix(key) % n);

        // --- FAST PATH (lock-free): find an existing bucket in the probe run.
        for (size_t i = 0; i < n; ++i) {
            Slot& slot = sh.slots[(home + i) % n];
            uint64_t k = slot.key.load(std::memory_order_acquire);
            if (k == key) {
                slot.ref.store(1, std::memory_order_relaxed);   // CLOCK reference
                return detail::try_consume_word(slot.word, now_ms, rate, cap);
            }
            if (k == EMPTY) break;  // open-addressing: run ended, key not present
        }

        // --- SLOW PATH (striped lock): insert or evict, then consume.
        std::lock_guard<std::mutex> lk(sh.mu);
        // Re-probe under the lock (another thread may have inserted meanwhile).
        for (size_t i = 0; i < n; ++i) {
            Slot& slot = sh.slots[(home + i) % n];
            uint64_t k = slot.key.load(std::memory_order_relaxed);
            if (k == key) {
                slot.ref.store(1, std::memory_order_relaxed);
                return detail::try_consume_word(slot.word, now_ms, rate, cap);
            }
            if (k == EMPTY) break;
        }
        Slot& target = sh.slots[acquire_slot(sh, home, n)];
        bind(target, key, now_ms, cap);
        return detail::try_consume_word(target.word, now_ms, rate, cap);
    }

    // --- introspection for tests ---
    size_t size() const {  // occupied slots
        size_t c = 0;
        for (auto& s : shards_)
            for (auto& slot : s.slots)
                if (slot.key.load(std::memory_order_relaxed) != EMPTY) ++c;
        return c;
    }
    size_t capacity() const {
        size_t c = 0;
        for (auto& s : shards_) c += s.slots.size();
        return c;
    }

private:
    static constexpr uint64_t EMPTY      = 0;
    static constexpr uint64_t SHARD_SALT = 0xD1B54A32D192ED03ull;

    struct Slot {
        std::atomic<uint64_t> key{EMPTY};
        std::atomic<uint64_t> word{0};
        std::atomic<uint8_t> ref{0};  // CLOCK reference bit
    };
    struct Shard {
        std::mutex mu;
        std::vector<Slot> slots;
    };
    std::vector<Shard> shards_;

    // Key 0 is the empty sentinel; remap incoming 0 to a fixed nonzero value.
    static uint64_t normalize(uint64_t key) {
        return key == EMPTY ? 0x9E3779B97F4A7C15ull : key;
    }
    // splitmix64 finalizer — cheap, good avalanche.
    static uint64_t mix(uint64_t x) {
        x += 0x9E3779B97F4A7C15ull;
        x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9ull;
        x = (x ^ (x >> 27)) * 0x94D049BB133111EBull;
        return x ^ (x >> 31);
    }

    // Pick a slot in the key's probe run to (re)use. Caller holds sh.mu.
    // Prefer an EMPTY slot; otherwise CLOCK second-chance within the run.
    static size_t acquire_slot(Shard& sh, size_t home, size_t n) {
        for (size_t i = 0; i < n; ++i) {
            size_t idx = (home + i) % n;
            if (sh.slots[idx].key.load(std::memory_order_relaxed) == EMPTY)
                return idx;
        }
        // Full: sweep the run clearing reference bits; the first clear one is the
        // victim. Two passes guarantee a victim (pass 1 clears all, pass 2 finds).
        for (size_t s = 0; s < 2 * n; ++s) {
            size_t idx = (home + (s % n)) % n;
            if (sh.slots[idx].ref.load(std::memory_order_relaxed) == 0) return idx;
            sh.slots[idx].ref.store(0, std::memory_order_relaxed);  // second chance
        }
        return home;  // unreachable
    }

    // Install a fresh, full bucket for `key`. Publish the key LAST with release
    // so a lock-free reader that sees the key also sees the initialized word.
    static void bind(Slot& slot, uint64_t key, uint32_t now_ms, uint32_t cap) {
        slot.word.store(detail::pack(now_ms, cap), std::memory_order_relaxed);
        slot.ref.store(1, std::memory_order_relaxed);
        slot.key.store(key, std::memory_order_release);
    }
};

}  // namespace rl
