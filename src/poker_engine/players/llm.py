"""LLM player — uses tool-calling to interact with the poker game."""

from __future__ import annotations

import json
from typing import Any, Protocol, runtime_checkable

from poker_engine.tools.adapters import adapt_tools
from poker_engine.tools.poker_tools import PokerToolkit


@runtime_checkable
class LLMAdapter(Protocol):
    """Minimal interface for LLM providers. Implement to plug in any provider."""

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        """Send messages + tools, return response with optional tool_calls.

        Returns:
            {"content": str | None,
             "tool_calls": [{"id": str, "name": str, "arguments": dict}]}
        """
        ...


DEFAULT_SYSTEM_PROMPT = """You are playing Texas Hold'em poker. \
Use the provided tools to view your cards, check equity, \
view opponents, and place your action. Think strategically \
about pot odds, position, and opponent tendencies. \
Always call place_action to make your move."""


class LLMPlayer:
    """A poker player powered by an LLM via tool-calling.

    The LLM sees the game through tools and makes decisions
    by calling place_action.
    """

    def __init__(
        self,
        name: str,
        adapter: LLMAdapter,
        toolkit: PokerToolkit,
        provider_format: str = "anthropic",
        system_prompt: str = "",
        temperature: float = 0.7,
        max_tool_rounds: int = 10,
        personality: str = "",
    ) -> None:
        self._name = name
        self._adapter = adapter
        self._toolkit = toolkit
        self._provider_format = provider_format
        self._temperature = temperature
        self._max_tool_rounds = max_tool_rounds
        self._conversation: list[dict[str, Any]] = []
        self._last_commentary: str | None = None

        if system_prompt:
            self._system_prompt = system_prompt
        elif personality:
            self._system_prompt = (
                f"{DEFAULT_SYSTEM_PROMPT}\n\nYour personality: {personality}"
            )
        else:
            self._system_prompt = DEFAULT_SYSTEM_PROMPT

    @property
    def name(self) -> str:
        return self._name

    async def decide(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        tool_schemas = adapt_tools(
            self._toolkit.get_tools(), self._provider_format
        )

        turn_msg = self._build_turn_prompt(game_state, valid_actions)
        self._conversation.append({"role": "user", "content": turn_msg})

        for _ in range(self._max_tool_rounds):
            response = await self._adapter.generate(
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    *self._conversation,
                ],
                tools=tool_schemas,
                temperature=self._temperature,
            )

            if not response.get("tool_calls"):
                self._last_commentary = response.get("content")
                return self._fallback_action(valid_actions)

            self._conversation.append({"role": "assistant", **response})

            for tc in response["tool_calls"]:
                result = self._toolkit.registry.call(
                    tc["name"], tc["arguments"]
                )
                self._conversation.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, default=str),
                })

                if tc["name"] == "place_action":
                    if isinstance(result, dict) and "error" not in result:
                        self._last_commentary = response.get("content")
                        return tc["arguments"]

        return {"action": "fold"}

    async def observe(self, event: dict[str, Any]) -> None:
        summary = json.dumps(event, default=str)
        self._conversation.append({
            "role": "user",
            "content": f"[Game event] {summary}",
        })

    async def get_commentary(self) -> str | None:
        return self._last_commentary

    def _build_turn_prompt(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> str:
        parts = [
            f"It's your turn. Phase: {game_state.get('phase', '?')}.",
            f"Pot: {game_state.get('pot', 0)}.",
        ]
        actions_str = ", ".join(
            a["action"] + (f"({a['amount']})" if a.get("amount") else "")
            for a in valid_actions
        )
        parts.append(f"Valid actions: {actions_str}")
        parts.append(
            "Use tools to check your cards and equity, then call "
            "place_action to make your move."
        )
        return " ".join(parts)

    @staticmethod
    def _fallback_action(
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        for a in valid_actions:
            if a["action"] in ("check", "call"):
                return a
        return valid_actions[0] if valid_actions else {"action": "fold"}
