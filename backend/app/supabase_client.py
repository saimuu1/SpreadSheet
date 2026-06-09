"""Supabase client factories.

Two clients, on purpose:

  * service client  — uses the service-role key, BYPASSES RLS. Used for trusted
    server-side work (e.g. reading a profile by id, Storage uploads). Never expose it.

  * user client     — uses the anon key but carries the caller's access token, so every
    PostgREST query runs as that user and Postgres RLS enforces owner isolation. This is
    the Builder/dashboard data path.
"""

from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import get_settings


@lru_cache
def get_service_client() -> Client:
    """Shared service-role client (bypasses RLS). Safe to cache — it has no per-request state."""
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def get_user_client(access_token: str) -> Client:
    """A client scoped to one Builder's access token, so RLS applies to every query."""
    settings = get_settings()
    client = create_client(settings.supabase_url, settings.supabase_anon_key)
    # Make PostgREST send the user's JWT so auth.uid() resolves inside RLS policies.
    client.postgrest.auth(access_token)
    return client
