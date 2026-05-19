"""@tool() decorator that marks functions as LLM-callable tools."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Any, Callable

from poker_engine.tools.schema import extract_schema


@dataclass(frozen=True)
class ToolDef:
    """Provider-agnostic tool definition with JSON Schema."""

    name: str
    description: str
    parameters: dict[str, Any]
    fn: Callable[..., Any]

    def to_schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.parameters,
        }


def tool(
    name: str | None = None,
    description: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that marks a function as an LLM-callable tool.

    JSON Schema is extracted from type hints and Google-style docstrings.
    """

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tool_name = name or fn.__name__
        raw_doc = inspect.cleandoc(fn.__doc__ or "")
        tool_desc = description or raw_doc.split("\n\n")[0].strip() or tool_name

        fn._tool_def = ToolDef(  # type: ignore[attr-defined]
            name=tool_name,
            description=tool_desc,
            parameters=extract_schema(fn),
            fn=fn,
        )
        return fn

    return decorator
