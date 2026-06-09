"""Rate limiting for the public API, backed by the request_logs table.

We count a key's requests in the trailing minute and day windows and compare against the
owner's plan. Over the limit -> 429. This is the entitlement logic the pricing tiers buy:
the limit is read from the plan, not faked in the UI.

Scaling note (interview talking point): counting rows in Postgres is fine to start; for
production scale this moves to Redis (e.g. a sliding window or token bucket) for speed.
"""

from __future__ import annotations

from fastapi import HTTPException, status

from app.services.plans import Plan

_COUNT_SQL = (
    "select count(*) from request_logs "
    "where api_key_id = $1 and created_at > now() - $2::interval"
)


async def enforce_and_log(conn, api_key_id: str, plan: Plan) -> None:
    """Raise 429 if the key is over its minute/day limit; otherwise record the request."""
    minute_count = await conn.fetchval(_COUNT_SQL, api_key_id, "1 minute")
    if minute_count >= plan.requests_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Rate limit exceeded: {plan.requests_per_minute} requests/minute on the "
                f"{plan.name} plan."
            ),
            headers={"Retry-After": "60"},
        )

    day_count = await conn.fetchval(_COUNT_SQL, api_key_id, "1 day")
    if day_count >= plan.requests_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Daily quota exceeded: {plan.requests_per_day} requests/day on the "
                f"{plan.name} plan."
            ),
            headers={"Retry-After": "3600"},
        )

    await conn.execute(
        "insert into request_logs (api_key_id) values ($1)", api_key_id
    )
