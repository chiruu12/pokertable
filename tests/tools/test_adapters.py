"""Tests for provider format adapters."""

from poker_engine.tools.adapters import adapt_tools, to_anthropic, to_google, to_openai
from poker_engine.tools.decorator import ToolDef, tool


def _sample_tool() -> ToolDef:
    @tool()
    def sample(x: int) -> str:
        """A sample tool.

        Args:
            x: A number.
        """
        return ""

    return sample._tool_def


def test_anthropic_format():
    td = _sample_tool()
    result = to_anthropic(td)
    assert result["name"] == "sample"
    assert result["description"] == "A sample tool."
    assert "input_schema" in result
    assert result["input_schema"]["properties"]["x"]["type"] == "integer"


def test_openai_format():
    td = _sample_tool()
    result = to_openai(td)
    assert result["type"] == "function"
    assert result["function"]["name"] == "sample"
    assert result["function"]["description"] == "A sample tool."
    assert "parameters" in result["function"]


def test_google_format():
    td = _sample_tool()
    result = to_google(td)
    assert result["name"] == "sample"
    assert "parameters" in result


def test_adapt_tools_batch():
    td = _sample_tool()
    schemas = adapt_tools([td, td], "openai")
    assert len(schemas) == 2
    assert all(s["type"] == "function" for s in schemas)


def test_adapt_tools_raw():
    td = _sample_tool()
    schemas = adapt_tools([td], "raw")
    assert schemas[0]["name"] == "sample"
    assert "input_schema" in schemas[0]
