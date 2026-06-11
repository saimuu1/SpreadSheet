"""Unit tests for the query parser and builder — pure logic, no database needed."""

import uuid

import pytest

from app.services.query_builder import build_query
from app.services.query_parser import QueryError, parse_query

COLUMNS = {
    "name": "text",
    "category": "text",
    "price": "number",
    "rating": "number",
    "in_stock": "boolean",
    "released": "date",
}


def test_eq_default_operator():
    spec = parse_query({"category": "protein"}, COLUMNS)
    assert len(spec.filters) == 1
    f = spec.filters[0]
    assert (f.field, f.op, f.value) == ("category", "eq", "protein")


def test_numeric_operator_coercion():
    spec = parse_query({"price__gt": "20"}, COLUMNS)
    f = spec.filters[0]
    assert (f.field, f.op, f.value) == ("price", "gt", 20)
    assert isinstance(f.value, int)


def test_float_value():
    spec = parse_query({"rating__gte": "4.5"}, COLUMNS)
    assert spec.filters[0].value == 4.5


def test_contains_only_on_text():
    spec = parse_query({"name__contains": "oil"}, COLUMNS)
    assert spec.filters[0].op == "contains"
    with pytest.raises(QueryError):
        parse_query({"price__contains": "2"}, COLUMNS)


def test_comparison_rejected_on_text():
    with pytest.raises(QueryError):
        parse_query({"name__gt": "a"}, COLUMNS)


def test_unknown_field_rejected():
    with pytest.raises(QueryError):
        parse_query({"bogus": "x"}, COLUMNS)


def test_bad_number_rejected():
    with pytest.raises(QueryError):
        parse_query({"price__gt": "abc"}, COLUMNS)


def test_boolean_coercion():
    spec = parse_query({"in_stock": "true"}, COLUMNS)
    assert spec.filters[0].value is True


def test_date_coercion():
    from datetime import date

    spec = parse_query({"released__gte": "2021-01-01"}, COLUMNS)
    assert spec.filters[0].value == date(2021, 1, 1)


def test_sort_desc_and_asc():
    assert parse_query({"sort": "-rating"}, COLUMNS).sort.direction == "desc"
    assert parse_query({"sort": "rating"}, COLUMNS).sort.direction == "asc"


def test_sort_unknown_field_rejected():
    with pytest.raises(QueryError):
        parse_query({"sort": "nope"}, COLUMNS)


def test_pagination_defaults_and_clamp():
    spec = parse_query({}, COLUMNS)
    assert (spec.page, spec.limit, spec.offset) == (1, 25, 0)
    spec = parse_query({"page": "3", "limit": "10"}, COLUMNS)
    assert (spec.page, spec.limit, spec.offset) == (3, 10, 20)
    assert parse_query({"limit": "9999"}, COLUMNS).limit == 100  # clamped to MAX_LIMIT


def test_builder_parameterizes_everything():
    spec = parse_query(
        {"category": "protein", "price__gt": "20", "sort": "-rating"}, COLUMNS
    )
    ds = uuid.uuid4()
    built = build_query(ds, spec)

    # Field names and values are bound, never interpolated: no literal field names in SQL.
    assert "data ->> $" in built.data_sql
    assert "protein" not in built.data_sql
    assert "category" not in built.data_sql
    assert "rating" not in built.data_sql
    # Params carry the actual data.
    assert "protein" in built.data_params
    assert 20 in built.data_params
    assert built.count_params == built.data_params[: len(built.count_params)]


def test_builder_injection_attempt_is_inert():
    # A malicious field would be rejected by the parser (unknown field) — but even if a
    # value contains SQL, it is a bound parameter, never executed.
    spec = parse_query({"name": "'; drop table rows; --"}, COLUMNS)
    built = build_query(uuid.uuid4(), spec)
    assert "drop table" not in built.data_sql.lower()
    assert "'; drop table rows; --" in built.data_params
