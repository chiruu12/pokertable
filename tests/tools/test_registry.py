"""Tests for the ToolRegistry — register, lookup, schema adapting, dispatch."""


import pytest

from poker_engine.tools.decorator import ToolDef, tool
from poker_engine.tools.registry import ToolRegistry

# ── helpers ──────────────────────────────────────────────────────────


@tool()
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}!"


@tool()
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(name="custom_name", description="Overridden desc")
def renamed() -> str:
    """Original doc."""
    return "ok"


@tool()
async def async_greet(name: str) -> str:
    """Async hello."""
    return f"Hi, {name}!"


# ── register ─────────────────────────────────────────────────────────


def test_register_single():
    reg = ToolRegistry()
    reg.register(greet)
    assert reg.get("greet") is not None


def test_register_all():
    reg = ToolRegistry()
    reg.register_all(greet, add)
    assert len(reg.list_tools()) == 2


def test_register_duplicate_raises():
    reg = ToolRegistry()
    reg.register(greet)
    with pytest.raises(ValueError, match="Duplicate tool name"):
        reg.register(greet)


# ── get / list ───────────────────────────────────────────────────────


def test_get_known_returns_tooldef():
    reg = ToolRegistry()
    reg.register(greet)
    td = reg.get("greet")
    assert isinstance(td, ToolDef)
    assert td.name == "greet"


def test_get_unknown_returns_none():
    reg = ToolRegistry()
    assert reg.get("nonexistent") is None


def test_list_tools_empty():
    reg = ToolRegistry()
    assert reg.list_tools() == []


def test_list_tools_order():
    reg = ToolRegistry()
    reg.register_all(greet, add)
    names = [t.name for t in reg.list_tools()]
    assert "greet" in names
    assert "add" in names


# ── get_schemas ──────────────────────────────────────────────────────


def test_get_schemas_anthropic():
    reg = ToolRegistry()
    reg.register(greet)
    schemas = reg.get_schemas("anthropic")
    assert len(schemas) == 1
    s = schemas[0]
    assert s["name"] == "greet"
    assert "input_schema" in s


def test_get_schemas_openai():
    reg = ToolRegistry()
    reg.register(greet)
    schemas = reg.get_schemas("openai")
    assert len(schemas) == 1
    s = schemas[0]
    assert s["type"] == "function"
    assert s["function"]["name"] == "greet"


def test_get_schemas_raw():
    reg = ToolRegistry()
    reg.register(greet)
    schemas = reg.get_schemas("raw")
    assert len(schemas) == 1
    assert schemas[0]["name"] == "greet"


def test_get_schemas_empty_registry():
    reg = ToolRegistry()
    assert reg.get_schemas("anthropic") == []


# ── call (sync) ──────────────────────────────────────────────────────


def test_call_dispatches_correctly():
    reg = ToolRegistry()
    reg.register(greet)
    result = reg.call("greet", {"name": "World"})
    assert result == "Hello, World!"


def test_call_with_multiple_args():
    reg = ToolRegistry()
    reg.register(add)
    assert reg.call("add", {"a": 3, "b": 4}) == 7


def test_call_unknown_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="Unknown tool"):
        reg.call("nope", {})


# ── call_async ───────────────────────────────────────────────────────


async def test_call_async_with_sync_fn():
    reg = ToolRegistry()
    reg.register(greet)
    result = await reg.call_async("greet", {"name": "Async"})
    assert result == "Hello, Async!"


async def test_call_async_with_native_async_fn():
    reg = ToolRegistry()
    reg.register(async_greet)
    result = await reg.call_async("async_greet", {"name": "Native"})
    assert result == "Hi, Native!"


async def test_call_async_unknown_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="Unknown tool"):
        await reg.call_async("missing", {})
