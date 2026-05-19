"""LangChain framework adapter — wraps any LangChain ChatModel.

Bridges poker tool schemas into LangChain's tool system and translates
between message formats.

Requires: pip install langchain langchain-anthropic (or langchain-openai)
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import StructuredTool


def poker_schemas_to_langchain_tools(
    schemas: list[dict[str, Any]],
) -> list[StructuredTool]:
    """Convert poker tool schemas (Anthropic format) to LangChain StructuredTools."""
    lc_tools = []
    for schema in schemas:
        name = schema["name"]
        desc = schema["description"]
        input_schema = schema.get("input_schema", {})

        def _noop(**kwargs: Any) -> str:
            return json.dumps({"info": "Tool executed via adapter, not directly."})

        tool = StructuredTool.from_function(
            func=_noop,
            name=name,
            description=desc,
        )
        if input_schema:
            tool.args_schema = None
        lc_tools.append(tool)
    return lc_tools


class LangChainAdapter:
    """Adapter that wraps a LangChain BaseChatModel as an LLMAdapter."""

    def __init__(self, chat_model: Any) -> None:
        self._model = chat_model

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        lc_messages = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                tc = msg.get("tool_calls", [])
                lc_tool_calls = [
                    {"id": t["id"], "name": t["name"], "args": t["arguments"]}
                    for t in tc
                ]
                lc_messages.append(AIMessage(
                    content=content or "",
                    tool_calls=lc_tool_calls,
                ))
            elif role == "tool":
                lc_messages.append(ToolMessage(
                    content=content,
                    tool_call_id=msg["tool_call_id"],
                ))

        lc_tools = poker_schemas_to_langchain_tools(tools) if tools else []
        model = self._model.bind_tools(lc_tools) if lc_tools else self._model

        response: AIMessage = await model.ainvoke(lc_messages)

        tool_calls = []
        for tc in response.tool_calls or []:
            tool_calls.append({
                "id": tc.get("id", ""),
                "name": tc["name"],
                "arguments": tc.get("args", {}),
            })

        return {
            "content": response.content if isinstance(response.content, str) else None,
            "tool_calls": tool_calls,
        }
