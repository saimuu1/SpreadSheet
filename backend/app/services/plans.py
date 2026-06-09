"""Tier definitions. Entitlements are enforced from these values in code (upload caps in
the datasets router; rate caps in the rate limiter) — the UI never decides limits.

Use -1 to mean "unlimited".
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    name: str
    max_datasets: int  # -1 = unlimited
    requests_per_day: int
    requests_per_minute: int
    allow_private: bool


PLANS: dict[str, Plan] = {
    "free": Plan(
        name="free",
        max_datasets=1,
        requests_per_day=1_000,
        requests_per_minute=10,
        allow_private=False,
    ),
    "pro": Plan(
        name="pro",
        max_datasets=-1,
        requests_per_day=100_000,
        requests_per_minute=120,
        allow_private=True,
    ),
}


def get_plan(plan_name: str | None) -> Plan:
    """Resolve a plan by name, defaulting to free for unknown/missing values."""
    return PLANS.get((plan_name or "free").lower(), PLANS["free"])
