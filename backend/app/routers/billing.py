"""Stripe billing — flat Pro subscription.

Flow:
  * POST /api/billing/checkout  (Builder auth) -> a Stripe Checkout URL to start the Pro sub.
  * POST /api/billing/portal    (Builder auth) -> a Stripe Customer Portal URL to manage/cancel.
  * POST /api/webhooks/stripe   (Stripe-signed) -> syncs subscription state to profiles.plan.

Stripe is the source of truth: our DB only ever changes plan in response to a verified
webhook, so a subscription starting flips plan to 'pro' and a cancellation flips it to 'free'.
"""

from __future__ import annotations

import json

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.config import get_settings
from app.db import get_pool
from app.dependencies import CurrentUser, get_current_user
from app.supabase_client import get_user_client

router = APIRouter(tags=["billing"])
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


def _require_stripe() -> None:
    if not settings.stripe_secret_key or not settings.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured (missing Stripe keys).",
        )


async def _get_or_create_customer(user: CurrentUser) -> str:
    """Return the user's Stripe customer id, creating + persisting it on first use."""
    client = get_user_client(user.access_token)
    prof = (
        client.table("profiles")
        .select("stripe_customer_id")
        .eq("id", user.id)
        .single()
        .execute()
    )
    existing = (prof.data or {}).get("stripe_customer_id")
    if existing:
        return existing
    customer = stripe.Customer.create(email=user.email, metadata={"user_id": user.id})
    client.table("profiles").update({"stripe_customer_id": customer.id}).eq(
        "id", user.id
    ).execute()
    return customer.id


@router.post("/api/billing/checkout")
async def create_checkout(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Start a Pro subscription — returns a hosted Stripe Checkout URL to redirect to."""
    _require_stripe()
    customer_id = await _get_or_create_customer(user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        customer=customer_id,
        client_reference_id=user.id,
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        subscription_data={"metadata": {"user_id": user.id}},
        success_url=f"{settings.frontend_url}/dashboard?checkout=success",
        cancel_url=f"{settings.frontend_url}/dashboard?checkout=cancel",
        allow_promotion_codes=True,
    )
    return {"url": session.url}


@router.post("/api/billing/portal")
async def create_portal(user: CurrentUser = Depends(get_current_user)) -> dict:
    """Open the Stripe Customer Portal so the user can update or cancel their subscription."""
    _require_stripe()
    customer_id = await _get_or_create_customer(user)
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{settings.frontend_url}/dashboard",
    )
    return {"url": session.url}


async def _set_plan(user_id: str, plan: str, subscription_id: str | None) -> None:
    """Update a profile's plan (service path — webhooks have no user JWT)."""
    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "update profiles set plan = $1, stripe_subscription_id = $2 where id = $3::uuid",
            plan,
            subscription_id,
            user_id,
        )


@router.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict:
    """Verify Stripe's signature, then mirror subscription state onto profiles.plan."""
    payload = await request.body()
    signature = request.headers.get("stripe-signature")
    try:
        # Verify the signature; we then read fields from the plain JSON payload.
        stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook signature verification failed: {exc}",
        ) from exc

    event = json.loads(payload)
    obj = event["data"]["object"]
    event_type = event["type"]

    if event_type == "checkout.session.completed":
        user_id = obj.get("client_reference_id")
        if user_id:
            await _set_plan(user_id, "pro", obj.get("subscription"))

    elif event_type in ("customer.subscription.created", "customer.subscription.updated"):
        user_id = (obj.get("metadata") or {}).get("user_id")
        if user_id:
            is_active = obj.get("status") in ("active", "trialing")
            await _set_plan(user_id, "pro" if is_active else "free",
                            obj.get("id") if is_active else None)

    elif event_type == "customer.subscription.deleted":
        user_id = (obj.get("metadata") or {}).get("user_id")
        if user_id:
            await _set_plan(user_id, "free", None)

    return {"received": True}
