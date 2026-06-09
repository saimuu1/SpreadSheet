"""Unit tests for schema inference — pure logic, no database needed."""

from app.services.inference import (
    build_row_objects,
    coerce_value,
    infer_column_type,
    infer_schema,
)


def test_number_column():
    assert infer_column_type(["1", "2.5", "3"]) == "number"


def test_boolean_column():
    assert infer_column_type(["true", "false", "yes", "no"]) == "boolean"


def test_date_column():
    assert infer_column_type(["2021-03-15", "2020-11-01"]) == "date"


def test_text_column():
    assert infer_column_type(["Creatine", "Whey", "Shaker"]) == "text"


def test_empty_and_null_tokens_are_ignored():
    # Mostly numbers with N/A and blanks => still number (nulls ignored).
    assert infer_column_type(["10", "", "N/A", "20", "-"]) == "number"


def test_one_stray_word_falls_back_to_text():
    # The defensible default: one non-numeric value keeps the whole column text.
    assert infer_column_type(["10", "20", "TBD"]) == "text"


def test_all_empty_is_text():
    assert infer_column_type(["", "N/A", None]) == "text"


def test_year_is_number_not_date():
    # Numbers are checked before dates, so a bare year stays a number.
    assert infer_column_type(["2021", "2022", "2023"]) == "number"


def test_month_word_is_text_not_date():
    # A value needs a digit to be considered a date.
    assert infer_column_type(["March", "April"]) == "text"


def test_coerce_values():
    assert coerce_value("24.99", "number") == 24.99
    assert coerce_value("3", "number") == 3  # integer-valued floats become ints
    assert coerce_value("yes", "boolean") is True
    assert coerce_value("no", "boolean") is False
    assert coerce_value("2021-03-15", "date") == "2021-03-15"
    assert coerce_value("", "number") is None
    assert coerce_value("N/A", "text") is None


def test_infer_schema_and_rows():
    headers = ["name", "price", "in_stock"]
    rows = [["Creatine", "24.99", "true"], ["Shaker", "9.50", "false"]]
    schema = infer_schema(headers, rows)
    types = {c["name"]: c["data_type"] for c in schema}
    assert types == {"name": "text", "price": "number", "in_stock": "boolean"}

    objects = build_row_objects(headers, rows, schema)
    assert objects[0] == {"name": "Creatine", "price": 24.99, "in_stock": True}
    assert objects[1] == {"name": "Shaker", "price": 9.50, "in_stock": False}
