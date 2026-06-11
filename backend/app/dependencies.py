"""FastAPI dependencies for the two authentication systems.

  * get_current_user  — Builder auth. Verifies a Supabase-issued JWT and returns the caller's
    identity plus their raw access token (needed to build an RLS-scoped Supabase client).
    Supports both modern asymmetric signing keys (ES256/RS256, verified against Supabase's
    public JWKS) and the legacy HS256 shared secret.

  * resolve_api_key   — Consumer auth. Hashes an incoming API key and resolves the owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import jwt
from fastapi import Header, HTTPException, status

from app.config import get_settings
from app.db import get_pool
from app.services.keys import hash_key

# Algorithms we accept for asymmetric (public-key) verification.
_ASYMMETRIC_ALGS = ["ES256", "RS256"]


@lru_cache
def _jwks_client() -> jwt.PyJWKClient:
    """Cached client that fetches + caches Supabase's public signing keys."""
    return jwt.PyJWKClient(get_settings().jwks_url)


def _decode_token(token: str) -> dict:
    """Verify a Supabase JWT, handling both signing schemes.

    We branch on the token header's `alg`:
      * HS256  -> verify with the shared JWT secret.
      * ES256/RS256 -> fetch the matching public key from JWKS and verify with it.
    Restricting each branch to a fixed algorithm set prevents alg-confusion attacks.
    """
    settings = get_settings()
    alg = jwt.get_unverified_header(token).get("alg")
    if alg == "HS256":
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    signing_key = _jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=_ASYMMETRIC_ALGS,
        audience="authenticated",
    )


@dataclass
class CurrentUser:
    id: str
    email: str | None
    access_token: str


@dataclass
class ConsumerContext:
    """Resolved identity for a public-API caller, derived from their API key."""

    api_key_id: str
    owner_id: str


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header. Expected 'Bearer <token>'.",
        )
    return authorization.split(" ", 1)[1].strip()


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    """Builder auth: validate the Supabase access token and return the user."""
    token = _bearer_token(authorization)
    try:
        payload = _decode_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {exc}",
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is missing a subject (sub) claim.",
        )
    return CurrentUser(id=user_id, email=payload.get("email"), access_token=token)


async def resolve_api_key(
    authorization: str | None = Header(default=None),
) -> ConsumerContext:
    """Consumer auth: hash the incoming API key, look it up, resolve the owner.

    Uses the direct asyncpg pool (service path, RLS bypassed) — authorization happens in
    application code, not via RLS.
    """
    raw_key = _bearer_token(authorization)
    key_hash = hash_key(raw_key)

    pool = get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "select id, owner_id from api_keys where key_hash = $1", key_hash
        )
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key."
            )
        await conn.execute(
            "update api_keys set last_used_at = now() where id = $1", row["id"]
        )
    return ConsumerContext(api_key_id=str(row["id"]), owner_id=str(row["owner_id"]))
