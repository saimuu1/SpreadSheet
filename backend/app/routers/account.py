"""Builder/dashboard account routes: profile + plan upgrade (stubbed payment)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.dependencies import CurrentUser, get_current_user
from app.models.schemas import ProfileOut
from app.supabase_client import get_user_client

router = APIRouter(prefix="/api/account", tags=["account"])


@router.get("/me", response_model=ProfileOut)
async def me(user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    """Return the caller's profile. Read via an RLS-scoped client, so the database
    itself guarantees the row belongs to the caller."""
    client = get_user_client(user.access_token)
    resp = client.table("profiles").select("*").eq("id", user.id).single().execute()
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found.",
        )
    return ProfileOut(**resp.data)


def _set_plan(user: CurrentUser, plan: str) -> ProfileOut:
    client = get_user_client(user.access_token)
    resp = (
        client.table("profiles").update({"plan": plan}).eq("id", user.id).execute()
    )
    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found."
        )
    return ProfileOut(**resp.data[0])


@router.post("/upgrade", response_model=ProfileOut)
async def upgrade(user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    """Stubbed payment: flip the plan to 'pro'. The real engineering is that the rate
    limiter and upload cap read this flag live — the checkout is intentionally faked."""
    return _set_plan(user, "pro")


@router.post("/downgrade", response_model=ProfileOut)
async def downgrade(user: CurrentUser = Depends(get_current_user)) -> ProfileOut:
    """Revert to the free plan (handy for testing tier enforcement)."""
    return _set_plan(user, "free")
