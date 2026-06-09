"""Direct Postgres access via an asyncpg pool.

This path is used by the *public Consumer API* only. It connects with the Supabase
database credentials (which bypass Row Level Security), so every query in this module
must enforce ownership in code and bind all user values as parameters.

The Builder/dashboard path does NOT use this module — it goes through the Supabase
client so that Postgres RLS enforces per-user isolation. See app/supabase_client.py.
"""

from __future__ import annotations

import json

import asyncpg

from app.config import get_settings

_pool: asyncpg.Pool | None = None


async def _init_connection(conn: asyncpg.Connection) -> None:
    # Decode jsonb columns straight into Python objects (asyncpg returns raw text otherwise).
    await conn.set_type_codec(
        "jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
    )


async def connect() -> None:
    """Open the shared connection pool. Called on app startup."""
    global _pool
    if _pool is None:
        settings = get_settings()
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=10,
            init=_init_connection,
            # Supabase requires SSL; asyncpg negotiates it from the sslmode in the DSN
            # or we can be explicit. 'require' works for both pooler and direct URIs.
            ssl="require",
        )


async def disconnect() -> None:
    """Close the pool. Called on app shutdown."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized. Did startup run?")
    return _pool
