"""Anthropic Claude adapter using the official anthropic SDK."""

from __future__ import annotations

import json
import os
from typing import Any

import anthropic


class AnthropicAdapter:
    """Adapter for Claude models via the official Anthropic Python SDK."""

    def __init__(self, model: str = "claude-haiku-4-5-20251001") -> None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        self._model = model
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        system_msg = ""
        api_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                system_msg = content

            elif role == "user":
                api_messages.append({"role": "user", "content": content})

            elif role == "assistant":
                blocks: list[dict[str, Any]] = []
                if content:
                    blocks.append({"type": "text", "text": content})
                for tc in msg.get("tool_calls", []):
                    blocks.append({
                        "type": "tool_use",
                        "id": tc["id"],
                        "name": tc["name"],
                        "input": tc["arguments"],
                    })
                api_messages.append({"role": "assistant", "content": blocks or content})

            elif role == "tool":
                tool_result = {
                    "type": "tool_result",
                    "tool_use_id": msg["tool_call_id"],
                    "content": content,
                }
                if api_messages and api_messages[-1]["role"] == "user":
                    existing = api_messages[-1]["content"]
                    if isinstance(existing, list):
                        existing.append(tool_result)
                    else:
                        api_messages[-1]["content"] = [tool_result]
                else:
                    api_messages.append({"role": "user", "content": [tool_result]})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 1024,
            "messages": api_messages,
            "temperature": temperature,
        }
        if system_msg:
            kwargs["system"] = system_msg
        if tools:
            kwargs["tools"] = tools

        response = await self._client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append({
                    "id": block.id,
                    "name": block.name,
                    "arguments": block.input,
                })

        return {
            "content": "\n".join(text_parts) if text_parts else None,
            "tool_calls": tool_calls,
        }

    async def close(self) -> None:
        await self._client.close()
