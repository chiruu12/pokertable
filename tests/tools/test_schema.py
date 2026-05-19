"""Tests for JSON Schema generation from type hints."""

from typing import Optional

from poker_engine.tools.schema import (
    extract_schema,
    parse_docstring_args,
    python_type_to_json_schema,
)


def test_str_type():
    assert python_type_to_json_schema(str) == {"type": "string"}


def test_int_type():
    assert python_type_to_json_schema(int) == {"type": "integer"}


def test_float_type():
    assert python_type_to_json_schema(float) == {"type": "number"}


def test_bool_type():
    assert python_type_to_json_schema(bool) == {"type": "boolean"}


def test_list_of_str():
    schema = python_type_to_json_schema(list[str])
    assert schema == {"type": "array", "items": {"type": "string"}}


def test_dict_str_int():
    schema = python_type_to_json_schema(dict[str, int])
    assert schema["type"] == "object"
    assert schema["additionalProperties"] == {"type": "integer"}


def test_optional_str():
    schema = python_type_to_json_schema(Optional[str])
    assert schema == {"type": "string"}


def test_parse_docstring_args_google_style():
    doc = """Do something cool.

    Args:
        name: The player name.
        amount: How much to bet.
    """
    result = parse_docstring_args(doc)
    assert result["name"] == "The player name."
    assert result["amount"] == "How much to bet."


def test_parse_docstring_args_with_type_hint():
    doc = """Foo.

    Args:
        count (int): Number of items.
    """
    result = parse_docstring_args(doc)
    assert result["count"] == "Number of items."


def test_extract_schema_simple():
    def my_func(name: str, count: int = 5) -> str:
        """A function.

        Args:
            name: The name.
            count: How many.
        """
        return ""

    schema = extract_schema(my_func)
    assert schema["type"] == "object"
    assert "name" in schema["properties"]
    assert "count" in schema["properties"]
    assert schema["properties"]["name"]["type"] == "string"
    assert schema["properties"]["count"]["type"] == "integer"
    assert "name" in schema["required"]
    assert "count" not in schema["required"]


def test_extract_schema_skips_self():
    class MyClass:
        def method(self, x: int) -> str:
            return ""

    schema = extract_schema(MyClass.method)
    assert "self" not in schema["properties"]
    assert "x" in schema["properties"]
