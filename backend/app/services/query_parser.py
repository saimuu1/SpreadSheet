"""The query parser: a tiny query language that lives in URL parameters.

    ?category=protein&price__gt=20&rating__gte=4.5&name__contains=oil&sort=-rating&page=1&limit=25

Each non-reserved param is a filter. The key is split on `__` to find an operator suffix
(defaulting to `eq`). Field names are whitelisted against the dataset's inferred schema, and
values are coerced using each field's type — so `price__gt=20` compares as a number, not text.

The output is a clean QuerySpec that the query builder (query_builder.py) turns into a
parameterized SQL statement. This module is pure and has no database dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from dateutil import parser as date_parser

RESERVED_PARAMS = {"sort", "page", "limit"}

# operator suffix -> internal op name
OPERATORS = {
    "gt": "gt",
    "lt": "lt",
    "gte": "gte",
    "lte": "lte",
    "contains": "contains",
}

COMPARISON_OPS = {"gt", "lt", "gte", "lte"}

DEFAULT_LIMIT = 25
MAX_LIMIT = 100


class QueryError(ValueError):
    """Raised on a malformed query — the router maps this to HTTP 400."""


@dataclass
class Filter:
    field: str
    op: str  # eq | gt | lt | gte | lte | contains
    value: object
    data_type: str  # text | number | boolean | date


@dataclass
class Sort:
    field: str
    direction: str  # asc | desc
    data_type: str


@dataclass
class QuerySpec:
    filters: list[Filter] = dataclass_field(default_factory=list)
    sort: Sort | None = None
    page: int = 1
    limit: int = DEFAULT_LIMIT

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


def _split_field_op(key: str) -> tuple[str, str]:
    """Split 'price__gt' -> ('price', 'gt'); 'category' -> ('category', 'eq')."""
    if "__" in key:
        field, _, suffix = key.rpartition("__")
        if suffix in OPERATORS and field:
            return field, OPERATORS[suffix]
    return key, "eq"


def _coerce_number(field: str, raw: str):
    try:
        num = float(raw)
    except ValueError:
        raise QueryError(f"Filter on '{field}' expects a number, got {raw!r}.") from None
    return int(num) if num.is_integer() else num


def _coerce_boolean(field: str, raw: str) -> bool:
    v = raw.strip().lower()
    if v in {"true", "1", "yes"}:
        return True
    if v in {"false", "0", "no"}:
        return False
    raise QueryError(f"Filter on '{field}' expects true/false, got {raw!r}.")


def _coerce_date(field: str, raw: str) -> str:
    try:
        return date_parser.parse(raw).date().isoformat()
    except (ValueError, OverflowError):
        raise QueryError(f"Filter on '{field}' expects a date, got {raw!r}.") from None


def _coerce_value(field: str, op: str, raw: str, data_type: str):
    # `contains` is a text search regardless of column type.
    if op == "contains":
        if data_type != "text":
            raise QueryError(f"'contains' is only valid on text fields, not '{field}'.")
        return raw
    if op in COMPARISON_OPS and data_type not in {"number", "date"}:
        raise QueryError(
            f"Operator '{op}' is only valid on number/date fields, not '{field}'."
        )
    if data_type == "number":
        return _coerce_number(field, raw)
    if data_type == "boolean":
        return _coerce_boolean(field, raw)
    if data_type == "date":
        return _coerce_date(field, raw)
    return raw  # text


def _parse_pagination(params: dict[str, str]) -> tuple[int, int]:
    page = 1
    limit = DEFAULT_LIMIT
    if "page" in params:
        try:
            page = int(params["page"])
        except ValueError:
            raise QueryError("'page' must be an integer.") from None
        if page < 1:
            raise QueryError("'page' must be >= 1.")
    if "limit" in params:
        try:
            limit = int(params["limit"])
        except ValueError:
            raise QueryError("'limit' must be an integer.") from None
        if limit < 1:
            raise QueryError("'limit' must be >= 1.")
        limit = min(limit, MAX_LIMIT)
    return page, limit


def _parse_sort(params: dict[str, str], columns: dict[str, str]) -> Sort | None:
    raw = params.get("sort")
    if not raw:
        return None
    direction = "asc"
    field = raw
    if raw.startswith("-"):
        direction = "desc"
        field = raw[1:]
    elif raw.startswith("+"):
        field = raw[1:]
    if field not in columns:
        raise QueryError(f"Unknown sort field: {field!r}.")
    return Sort(field=field, direction=direction, data_type=columns[field])


def parse_query(params: dict[str, str], columns: dict[str, str]) -> QuerySpec:
    """Turn raw query params into a validated QuerySpec.

    `columns` maps field name -> data_type for this dataset (the whitelist).
    """
    filters: list[Filter] = []
    for key, raw in params.items():
        if key in RESERVED_PARAMS:
            continue
        field, op = _split_field_op(key)
        if field not in columns:
            raise QueryError(f"Unknown field: {field!r}.")
        data_type = columns[field]
        value = _coerce_value(field, op, raw, data_type)
        filters.append(Filter(field=field, op=op, value=value, data_type=data_type))

    page, limit = _parse_pagination(params)
    sort = _parse_sort(params, columns)
    return QuerySpec(filters=filters, sort=sort, page=page, limit=limit)
