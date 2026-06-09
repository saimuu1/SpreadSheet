"""Schema inference: teach the API the shape of an uploaded CSV.

For each column we sample its values and decide one of: number, boolean, date, text.

The judgment calls (these are deliberate, defensible choices):

  * Empty-ish cells are ignored when deciding a type. We treat "", whitespace, and the
    common null sentinels ("n/a", "na", "null", "none", "-") as missing, not as text.
  * A column gets a non-text type only if EVERY non-empty value fits that type. If even one
    value doesn't fit, we keep the column as `text`. Rationale: silently mis-typing a column
    (e.g. calling it `number` when one row says "TBD") would make range filters compare the
    wrong thing. Falling back to text is the safe default.
  * Detection order is boolean → number → date. Numbers are checked before dates because a
    bare year like "2023" is both; treating it as a number is the less surprising choice.
  * A value must contain a digit to be considered a date, so month/day words ("March",
    "Monday") stay text rather than being coerced to the current year by a liberal parser.
"""

from __future__ import annotations

from dateutil import parser as date_parser

NULL_TOKENS = {"", "n/a", "na", "null", "none", "-"}
TRUE_TOKENS = {"true", "yes", "t", "y"}
FALSE_TOKENS = {"false", "no", "f", "n"}

DataType = str  # one of: "text" | "number" | "boolean" | "date"


def is_empty(value: str | None) -> bool:
    return value is None or value.strip().lower() in NULL_TOKENS


def _is_bool(value: str) -> bool:
    v = value.strip().lower()
    return v in TRUE_TOKENS or v in FALSE_TOKENS


def _is_number(value: str) -> bool:
    v = value.strip()
    try:
        num = float(v)
    except (ValueError, TypeError):
        return False
    # Reject inf/nan, which float() happily accepts.
    return num == num and num not in (float("inf"), float("-inf"))


def _is_date(value: str) -> bool:
    v = value.strip()
    if not any(ch.isdigit() for ch in v):
        return False
    try:
        date_parser.parse(v)
        return True
    except (ValueError, OverflowError):
        return False


def infer_column_type(values: list[str | None]) -> DataType:
    """Decide the type for one column from its raw string values."""
    non_empty = [v.strip() for v in values if not is_empty(v)]  # type: ignore[union-attr]
    if not non_empty:
        return "text"
    if all(_is_bool(v) for v in non_empty):
        return "boolean"
    if all(_is_number(v) for v in non_empty):
        return "number"
    if all(_is_date(v) for v in non_empty):
        return "date"
    return "text"


def coerce_value(value: str | None, data_type: DataType):
    """Convert a raw CSV cell to the typed Python value stored in jsonb.

    Empty-ish cells always become null, regardless of the column type.
    """
    if is_empty(value):
        return None
    v = value.strip()  # type: ignore[union-attr]
    if data_type == "number":
        num = float(v)
        return int(num) if num.is_integer() else num
    if data_type == "boolean":
        return v.lower() in TRUE_TOKENS
    if data_type == "date":
        # Store as ISO-8601 so it sorts and compares correctly as text in jsonb.
        return date_parser.parse(v).date().isoformat()
    return v


def infer_schema(headers: list[str], rows: list[list[str]]) -> list[dict]:
    """Return [{name, data_type, position}] for each column.

    `rows` is a list of cell lists aligned to `headers`.
    """
    schema: list[dict] = []
    for position, name in enumerate(headers):
        column_values = [row[position] if position < len(row) else None for row in rows]
        schema.append(
            {
                "name": name,
                "data_type": infer_column_type(column_values),
                "position": position,
            }
        )
    return schema


def build_row_objects(
    headers: list[str], rows: list[list[str]], schema: list[dict]
) -> list[dict]:
    """Turn raw CSV rows into typed JSON objects keyed by column name."""
    type_by_position = {col["position"]: col["data_type"] for col in schema}
    objects: list[dict] = []
    for row in rows:
        obj: dict = {}
        for position, name in enumerate(headers):
            raw = row[position] if position < len(row) else None
            obj[name] = coerce_value(raw, type_by_position[position])
        objects.append(obj)
    return objects
