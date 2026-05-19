"""Provider format adapters for tool schemas."""

from __future__ import annotations

from typing import Any, Callable

from poker_engine.tools.decorator import ToolDef


def to_anthropic(td: ToolDef) -> dict[str, Any]:
    return td.to_schema()


def to_openai(td: ToolDef) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": td.name,
            "description": td.description,
            "parameters": td.parameters,
        },
    }


def to_google(td: ToolDef) -> dict[str, Any]:
    return {
        "name": td.name,
        "description": td.description,
        "parameters": td.parameters,
    }


ADAPTERS: dict[str, Callable[[ToolDef], dict[str, Any]]] = {
    "anthropic": to_anthropic,
    "openai": to_openai,
    "google": to_google,
    "raw": lambda td: td.to_schema(),
}


def adapt_tools(tools: list[ToolDef], provider: str) -> list[dict[str, Any]]:
    adapter = ADAPTERS.get(provider)
    if adapter is None:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(ADAPTERS)}")
    return [adapter(t) for t in tools]
