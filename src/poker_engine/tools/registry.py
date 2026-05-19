"""Tool registry — collect, lookup, and dispatch tool calls."""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, Callable

from poker_engine.tools.adapters import adapt_tools
from poker_engine.tools.decorator import ToolDef


class ToolRegistry:
    """Collects tools, validates inputs, dispatches calls."""

    def __init__(self) -> None:
        self._tools: dict[str, ToolDef] = {}

    def register(self, fn: Callable[..., Any]) -> None:
        td: ToolDef = fn._tool_def  # type: ignore[attr-defined]
        if td.name in self._tools:
            raise ValueError(f"Duplicate tool name: {td.name}")
        # Store the passed-in fn (which may be a bound method) instead of
        # td.fn (which is the unbound function from the @tool decorator).
        bound_td = ToolDef(
            name=td.name,
            description=td.description,
            parameters=td.parameters,
            fn=fn,
        )
        self._tools[td.name] = bound_td

    def register_all(self, *fns: Callable[..., Any]) -> None:
        for fn in fns:
            self.register(fn)

    def get(self, name: str) -> ToolDef | None:
        return self._tools.get(name)

    def list_tools(self) -> list[ToolDef]:
        return list(self._tools.values())

    def get_schemas(self, provider: str = "raw") -> list[dict[str, Any]]:
        return adapt_tools(list(self._tools.values()), provider)

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        td = self._tools.get(name)
        if td is None:
            raise KeyError(f"Unknown tool: {name}")
        return td.fn(**arguments)

    async def call_async(self, name: str, arguments: dict[str, Any]) -> Any:
        td = self._tools.get(name)
        if td is None:
            raise KeyError(f"Unknown tool: {name}")
        if inspect.iscoroutinefunction(td.fn):
            return await td.fn(**arguments)
        return await asyncio.to_thread(td.fn, **arguments)
