"""API key generation and hashing.

We store only a SHA-256 hash of each key plus a short non-secret prefix (so the Builder can
tell keys apart in the dashboard). The raw key is shown exactly once, at creation. This is
the same model as a password: if the database leaks, the keys aren't usable.
"""

from __future__ import annotations

import hashlib
import secrets

KEY_PREFIX = "sk_live_"
PREFIX_DISPLAY_LEN = 12  # chars of the raw key kept for display, e.g. "sk_live_a8f3"


def hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_key() -> tuple[str, str, str]:
    """Return (raw_key, key_hash, key_prefix). Only the hash + prefix get persisted."""
    raw_key = KEY_PREFIX + secrets.token_urlsafe(32)
    return raw_key, hash_key(raw_key), raw_key[:PREFIX_DISPLAY_LEN]
