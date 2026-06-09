"""Builder/dashboard dataset routes: upload, list, schema, delete.

All DB access here goes through the RLS-scoped user client, so the database enforces that
a Builder only ever touches their own datasets.
"""

from __future__ import annotations

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.config import get_settings
from app.dependencies import CurrentUser, get_current_user
from app.models.schemas import (
    ColumnOut,
    DatasetDetail,
    DatasetDocs,
    DatasetSummary,
    FieldDoc,
)
from app.services.inference import build_row_objects, infer_schema
from app.services.plans import get_plan
from app.supabase_client import get_service_client, get_user_client

router = APIRouter(prefix="/api/datasets", tags=["datasets"])

ROW_INSERT_CHUNK = 500

# Which query operators each inferred type supports (drives the auto-generated docs).
OPERATORS_BY_TYPE = {
    "text": ["eq", "contains"],
    "number": ["eq", "gt", "lt", "gte", "lte"],
    "date": ["eq", "gt", "lt", "gte", "lte"],
    "boolean": ["eq"],
}


def _parse_csv(raw: bytes) -> tuple[list[str], list[list[str]]]:
    text = raw.decode("utf-8-sig")  # utf-8-sig strips a BOM if present
    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if r]  # drop fully blank lines
    if not rows:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="CSV is empty."
        )
    headers = [h.strip() for h in rows[0]]
    if not headers or any(h == "" for h in headers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CSV header row has blank column names.",
        )
    return headers, rows[1:]


@router.post("", response_model=DatasetDetail, status_code=status.HTTP_201_CREATED)
async def upload_dataset(
    file: UploadFile,
    name: str | None = None,
    user: CurrentUser = Depends(get_current_user),
) -> DatasetDetail:
    client = get_user_client(user.access_token)

    # --- enforce the plan's dataset cap (entitlement logic, not UI) ---
    profile = client.table("profiles").select("plan").eq("id", user.id).single().execute()
    plan = get_plan(profile.data.get("plan") if profile.data else "free")
    if plan.max_datasets != -1:
        existing = (
            client.table("datasets").select("id", count="exact").eq("owner_id", user.id).execute()
        )
        if (existing.count or 0) >= plan.max_datasets:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=(
                    f"The {plan.name} plan allows {plan.max_datasets} dataset(s). "
                    "Upgrade to Pro for unlimited datasets."
                ),
            )

    # --- read + parse the file ---
    raw = await file.read()
    headers, data_rows = _parse_csv(raw)
    schema = infer_schema(headers, data_rows)
    row_objects = build_row_objects(headers, data_rows, schema)
    dataset_name = name or (file.filename or "dataset").rsplit(".", 1)[0]

    # --- create the dataset row (RLS: owner_id must equal auth.uid()) ---
    created = (
        client.table("datasets")
        .insert({"owner_id": user.id, "name": dataset_name, "row_count": len(row_objects)})
        .execute()
    )
    dataset = created.data[0]
    dataset_id = dataset["id"]

    # --- store the raw upload in Storage (service client) ---
    try:
        bucket = get_settings().storage_bucket
        storage_path = f"{user.id}/{dataset_id}.csv"
        get_service_client().storage.from_(bucket).upload(
            storage_path, raw, {"content-type": "text/csv", "upsert": "true"}
        )
    except Exception:  # noqa: BLE001
        # Storage is a nice-to-have copy of the raw file; don't fail the upload over it.
        pass

    # --- insert columns ---
    client.table("columns").insert(
        [{"dataset_id": dataset_id, **col} for col in schema]
    ).execute()

    # --- insert rows in chunks ---
    for start in range(0, len(row_objects), ROW_INSERT_CHUNK):
        chunk = row_objects[start : start + ROW_INSERT_CHUNK]
        client.table("rows").insert(
            [{"dataset_id": dataset_id, "data": obj} for obj in chunk]
        ).execute()

    return DatasetDetail(
        id=dataset_id,
        name=dataset_name,
        row_count=len(row_objects),
        created_at=dataset.get("created_at"),
        columns=[ColumnOut(**col) for col in schema],
    )


@router.get("", response_model=list[DatasetSummary])
async def list_datasets(user: CurrentUser = Depends(get_current_user)) -> list[DatasetSummary]:
    client = get_user_client(user.access_token)
    resp = (
        client.table("datasets")
        .select("id,name,row_count,created_at")
        .order("created_at", desc=True)
        .execute()
    )
    return [DatasetSummary(**d) for d in resp.data]


@router.get("/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(
    dataset_id: str, user: CurrentUser = Depends(get_current_user)
) -> DatasetDetail:
    client = get_user_client(user.access_token)
    ds = client.table("datasets").select("*").eq("id", dataset_id).execute()
    if not ds.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    dataset = ds.data[0]
    cols = (
        client.table("columns")
        .select("name,data_type,position")
        .eq("dataset_id", dataset_id)
        .order("position")
        .execute()
    )
    return DatasetDetail(
        id=dataset["id"],
        name=dataset["name"],
        row_count=dataset["row_count"],
        created_at=dataset.get("created_at"),
        columns=[ColumnOut(**c) for c in cols.data],
    )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: str, user: CurrentUser = Depends(get_current_user)
) -> None:
    client = get_user_client(user.access_token)
    # ON DELETE CASCADE removes columns + rows. RLS ensures only the owner can delete.
    client.table("datasets").delete().eq("id", dataset_id).execute()


@router.get("/{dataset_id}/docs", response_model=DatasetDocs)
async def dataset_docs(
    dataset_id: str, user: CurrentUser = Depends(get_current_user)
) -> DatasetDocs:
    """Auto-generated API docs for one dataset: the endpoint, fields, supported operators,
    and an example query. The frontend renders this; here it's the data behind it."""
    client = get_user_client(user.access_token)
    ds = client.table("datasets").select("id,name").eq("id", dataset_id).execute()
    if not ds.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found.")
    cols = (
        client.table("columns")
        .select("name,data_type,position")
        .eq("dataset_id", dataset_id)
        .order("position")
        .execute()
    )
    fields = [
        FieldDoc(
            name=c["name"],
            data_type=c["data_type"],
            operators=OPERATORS_BY_TYPE.get(c["data_type"], ["eq"]),
        )
        for c in cols.data
    ]

    # Build a realistic example using the first comparable/text field if present.
    example_parts = []
    for f in fields:
        if f.data_type == "number":
            example_parts.append(f"{f.name}__gt=0")
            break
    for f in fields:
        if f.data_type == "text":
            example_parts.append(f"sort=-{fields[0].name}" if fields else "")
            break
    example_qs = "&".join(p for p in [*example_parts, "page=1", "limit=25"] if p)
    endpoint = f"/api/v1/datasets/{dataset_id}"

    return DatasetDocs(
        dataset_id=dataset_id,
        name=ds.data[0]["name"],
        endpoint=endpoint,
        auth="Authorization: Bearer <your api key>",
        fields=fields,
        example=f"GET {endpoint}?{example_qs}",
    )
