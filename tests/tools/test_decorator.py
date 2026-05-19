"""Tests for the @tool() decorator."""

from poker_engine.tools.decorator import ToolDef, tool


def test_tool_decorator_basic():
    @tool()
    def greet(name: str) -> str:
        """Say hello."""
        return f"Hello {name}"

    assert hasattr(greet, "_tool_def")
    td: ToolDef = greet._tool_def
    assert td.name == "greet"
    assert td.description == "Say hello."
    assert "name" in td.parameters["properties"]


def test_tool_decorator_custom_name():
    @tool(name="my_tool", description="Custom desc")
    def func(x: int) -> int:
        return x

    td: ToolDef = func._tool_def
    assert td.name == "my_tool"
    assert td.description == "Custom desc"


def test_tool_decorator_preserves_function():
    @tool()
    def add(a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    assert add(3, 4) == 7


def test_tool_def_to_schema():
    @tool()
    def bet(amount: int) -> str:
        """Place a bet.

        Args:
            amount: Chips to bet.
        """
        return ""

    schema = bet._tool_def.to_schema()
    assert schema["name"] == "bet"
    assert schema["description"] == "Place a bet."
    assert "input_schema" in schema
    assert schema["input_schema"]["properties"]["amount"]["description"] == "Chips to bet."


def test_tool_with_defaults():
    @tool()
    def action(move: str, amount: int = 0) -> str:
        """Do something.

        Args:
            move: The action type.
            amount: Optional amount.
        """
        return ""

    td: ToolDef = action._tool_def
    assert "move" in td.parameters.get("required", [])
    assert "amount" not in td.parameters.get("required", [])
