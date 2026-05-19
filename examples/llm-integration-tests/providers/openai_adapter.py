"""OpenAI-compatible adapter using the official openai SDK.

Works with: OpenAI, LM Studio, Fireworks AI, vLLM, Ollama, Together AI.
"""

from __future__ import annotations

import json
import os
from typing import Any

import openai


class OpenAIAdapter:
    """Adapter for OpenAI-compatible APIs via the official openai SDK."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("OPENAI_API_KEY", "not-needed")
        self._model = model
        self._client = openai.AsyncOpenAI(
            api_key=resolved_key,
            base_url=base_url,
        )

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        api_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role in ("system", "user"):
                api_messages.append({"role": role, "content": content})

            elif role == "assistant":
                entry: dict[str, Any] = {"role": "assistant"}
                if content:
                    entry["content"] = content
                tc_list = msg.get("tool_calls", [])
                if tc_list:
                    entry["tool_calls"] = [
                        {
                            "id": tc["id"],
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": json.dumps(tc["arguments"]),
                            },
                        }
                        for tc in tc_list
                    ]
                api_messages.append(entry)

            elif role == "tool":
                api_messages.append({
                    "role": "tool",
                    "tool_call_id": msg["tool_call_id"],
                    "content": content,
                })

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": api_messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools

        response = await self._client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        tool_calls = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        return {
            "content": choice.content,
            "tool_calls": tool_calls,
        }

    async def close(self) -> None:
        await self._client.close()
