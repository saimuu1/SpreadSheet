"""Turn a QuerySpec into a parameterized SQL query over the jsonb `rows.data` column.

Security model (the point interviewers poke at):
  * Field names are NOT string-interpolated. We read jsonb values with `data ->> $n`, binding
    the field name itself as a query parameter. Combined with the parser whitelisting fields
    against the dataset schema, a caller can never inject a column name or alter the query.
  * Every filter value is bound as a parameter too. User input is always data, never SQL.

asyncpg uses positional placeholders ($1, $2, ...); we track them as we append params.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.services.query_parser import Filter, QuerySpec, Sort

_OP_SQL = {"eq": "=", "gt": ">", "lt": "<", "gte": ">=", "lte": "<="}


@dataclass
class BuiltQuery:
    data_sql: str
    data_params: list
    count_sql: str
    count_params: list


class _Params:
    """Accumulates bind parameters and hands back $N placeholders."""

    def __init__(self) -> None:
        self.values: list = []

    def add(self, value) -> str:
        self.values.append(value)
        return f"${len(self.values)}"


def _typed_lhs(field_ph: str, data_type: str) -> str:
    """Left-hand side: the jsonb value, cast to the comparable type."""
    accessor = f"(data ->> {field_ph})"
    if data_type == "number":
        return f"{accessor}::numeric"
    if data_type == "date":
        return f"{accessor}::date"
    if data_type == "boolean":
        return f"{accessor}::boolean"
    return accessor  # text


def _filter_clause(f: Filter, params: _Params) -> str:
    field_ph = params.add(f.field)
    lhs = _typed_lhs(field_ph, f.data_type)

    if f.op == "contains":
        value_ph = params.add(f"%{f.value}%")
        return f"{lhs} ILIKE {value_ph}"

    value_ph = params.add(f.value)
    return f"{lhs} {_OP_SQL[f.op]} {value_ph}"


def _order_by(sort: Sort, params: _Params) -> str:
    field_ph = params.add(sort.field)
    lhs = _typed_lhs(field_ph, sort.data_type)
    direction = "desc" if sort.direction == "desc" else "asc"
    # NULLS LAST keeps missing values out of the way in both directions.
    return f"order by {lhs} {direction} nulls last"


def build_query(dataset_id: uuid.UUID, spec: QuerySpec) -> BuiltQuery:
    params = _Params()
    dataset_ph = params.add(dataset_id)
    where = [f"dataset_id = {dataset_ph}"]
    for f in spec.filters:
        where.append(_filter_clause(f, params))
    where_sql = " and ".join(where)

    # Count query shares the WHERE params exactly (no limit/offset).
    count_sql = f"select count(*) from rows where {where_sql}"
    count_params = list(params.values)

    # Data query adds ordering + pagination.
    order_sql = _order_by(spec.sort, params) if spec.sort else "order by id"
    limit_ph = params.add(spec.limit)
    offset_ph = params.add(spec.offset)
    data_sql = (
        f"select data from rows where {where_sql} {order_sql} "
        f"limit {limit_ph} offset {offset_ph}"
    )
    return BuiltQuery(
        data_sql=data_sql,
        data_params=list(params.values),
        count_sql=count_sql,
        count_params=count_params,
    )
