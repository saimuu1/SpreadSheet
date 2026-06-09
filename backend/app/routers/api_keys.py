"""Builder/dashboard API-key routes: create, list, revoke.

These manage the credential the Consumer later sends to the public API. DB access is
RLS-scoped, so a Builder only sees their own keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.dependencies import CurrentUser, get_current_user
from app.models.schemas import ApiKeyCreated, ApiKeyOut
from app.services.keys import generate_key
from app.supabase_client import get_user_client

router = APIRouter(prefix="/api/keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_key(user: CurrentUser = Depends(get_current_user)) -> ApiKeyCreated:
    raw_key, key_hash, key_prefix = generate_key()
    client = get_user_client(user.access_token)
    created = (
        client.table("api_keys")
        .insert({"owner_id": user.id, "key_hash": key_hash, "key_prefix": key_prefix})
        .execute()
    )
    row = created.data[0]
    # The raw key is returned here and never again.
    return ApiKeyCreated(
        id=row["id"],
        key_prefix=row["key_prefix"],
        created_at=row.get("created_at"),
        last_used_at=row.get("last_used_at"),
        key=raw_key,
    )


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(user: CurrentUser = Depends(get_current_user)) -> list[ApiKeyOut]:
    client = get_user_client(user.access_token)
    resp = (
        client.table("api_keys")
        .select("id,key_prefix,created_at,last_used_at")
        .order("created_at", desc=True)
        .execute()
    )
    return [ApiKeyOut(**k) for k in resp.data]


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_key(key_id: str, user: CurrentUser = Depends(get_current_user)) -> None:
    client = get_user_client(user.access_token)
    client.table("api_keys").delete().eq("id", key_id).execute()
