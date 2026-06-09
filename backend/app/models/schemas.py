"""Pydantic request/response models shared across routers."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


# ----- account ------------------------------------------------------------------
class ProfileOut(BaseModel):
    id: str
    email: str | None
    plan: str
    created_at: datetime | None = None


# ----- datasets (Phase 2) -------------------------------------------------------
class ColumnOut(BaseModel):
    name: str
    data_type: str
    position: int


class DatasetSummary(BaseModel):
    id: str
    name: str
    row_count: int
    created_at: datetime | None = None


class DatasetDetail(DatasetSummary):
    columns: list[ColumnOut]


# ----- api keys (Phase 3) -------------------------------------------------------
class ApiKeyOut(BaseModel):
    id: str
    key_prefix: str
    created_at: datetime | None = None
    last_used_at: datetime | None = None


class ApiKeyCreated(ApiKeyOut):
    # The raw key is returned exactly once, at creation time.
    key: str


# ----- public API (Phase 4/5) ---------------------------------------------------
class QueryResponse(BaseModel):
    data: list[dict]
    page: int
    limit: int
    total: int


# ----- per-dataset docs (Phase 7) -----------------------------------------------
class FieldDoc(BaseModel):
    name: str
    data_type: str
    operators: list[str]


class DatasetDocs(BaseModel):
    dataset_id: str
    name: str
    endpoint: str
    auth: str
    fields: list[FieldDoc]
    example: str
