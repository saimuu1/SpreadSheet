"""The public Consumer API.

  GET /api/v1/datasets/{id}?<filters>&sort=...&page=&limit=
  Header: Authorization: Bearer <api key>

Pipeline (blueprint §4): authenticate (resolve_api_key) → authorize (owner check) →
[rate limit — Phase 6] → parse query (Phase 5) → safe query → format & respond.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.db import get_pool
from app.dependencies import ConsumerContext, resolve_api_key
from app.models.schemas import QueryResponse
from app.services.plans import get_plan
from app.services.query_builder import build_query
from app.services.query_parser import QueryError, parse_query
from app.services.rate_limit import check_rate_limit

router = APIRouter(prefix="/api/v1/datasets", tags=["public-api"])


def _parse_uuid(dataset_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(dataset_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found."
        ) from None


async def _authorize_dataset(conn, dataset_uuid: uuid.UUID, owner_id: str) -> None:
    owner = await conn.fetchval(
        "select owner_id from datasets where id = $1", dataset_uuid
    )
    if owner is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    if str(owner) != owner_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This API key does not have access to this dataset.",
        )


async def _load_columns(conn, dataset_uuid: uuid.UUID) -> dict[str, str]:
    """Field-name -> data_type map; the whitelist the parser validates against."""
    rows = await conn.fetch(
        "select name, data_type from columns where dataset_id = $1", dataset_uuid
    )
    return {r["name"]: r["data_type"] for r in rows}


@router.get("/{dataset_id}", response_model=QueryResponse)
async def query_dataset(
    dataset_id: str,
    request: Request,
    ctx: ConsumerContext = Depends(resolve_api_key),
) -> QueryResponse:
    dataset_uuid = _parse_uuid(dataset_id)
    pool = get_pool()
    async with pool.acquire() as conn:
        await _authorize_dataset(conn, dataset_uuid, ctx.owner_id)

        # Rate limit (step 3): in-memory token bucket (native C++, O(1), no DB
        # round-trip). Replaces the old racy `count(*)` over request_logs.
        plan_name = await conn.fetchval(
            "select plan from profiles where id = $1", ctx.owner_id
        )
        check_rate_limit(ctx.api_key_id, get_plan(plan_name))

        columns = await _load_columns(conn, dataset_uuid)

        # Parse + validate the URL query against the dataset's schema.
        try:
            spec = parse_query(dict(request.query_params), columns)
        except QueryError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
            ) from exc

        built = build_query(dataset_uuid, spec)
        total = await conn.fetchval(built.count_sql, *built.count_params)
        rows = await conn.fetch(built.data_sql, *built.data_params)

    data = [r["data"] for r in rows]
    return QueryResponse(data=data, page=spec.page, limit=spec.limit, total=total or 0)
