"""Agno framework adapter — uses Agno's Agent with native tool support.

Agno agents run their own tool-calling loop, so we bridge by:
1. Converting poker ToolDefs into Agno-compatible tool functions
2. Letting the Agno Agent call tools and return the final action

Requires: pip install agno
"""

from __future__ import annotations

import json
from typing import Any

from agno.agent import Agent as AgnoAgent
from agno.models.anthropic import Claude


def make_agno_tools(toolkit: Any) -> list:
    """Convert PokerToolkit methods into plain functions Agno can call."""
    from agno.tools import tool as agno_tool

    tools = []

    @agno_tool
    def view_hand() -> str:
        """View your hole cards and current hand strength."""
        return json.dumps(toolkit.view_hand())

    @agno_tool
    def view_table() -> str:
        """View the community cards, pot size, current bet, and game phase."""
        return json.dumps(toolkit.view_table())

    @agno_tool
    def check_equity(num_simulations: int = 500) -> str:
        """Calculate your win probability using Monte Carlo simulation."""
        return json.dumps(toolkit.check_equity(num_simulations=num_simulations))

    @agno_tool
    def view_opponents() -> str:
        """View public information about all opponents."""
        return json.dumps(toolkit.view_opponents())

    @agno_tool
    def place_action(action: str, amount: int = 0) -> str:
        """Place your poker action: fold, check, call, raise, or all_in."""
        return json.dumps(toolkit.place_action(action=action, amount=amount))

    tools = [view_hand, view_table, check_equity, view_opponents, place_action]
    return tools


class AgnoAdapter:
    """Adapter that wraps an Agno Agent as an LLMAdapter.

    The Agno agent handles its own tool-calling loop internally.
    We ask it to make a poker decision, and it uses the tools we provide.
    """

    def __init__(
        self,
        toolkit: Any,
        model: str = "claude-haiku-4-5-20251001",
        system_prompt: str = "",
    ) -> None:
        agno_tools = make_agno_tools(toolkit)

        self._agent = AgnoAgent(
            model=Claude(id=model),
            tools=agno_tools,
            instructions=(
                system_prompt
                or "You are playing Texas Hold'em poker. Use the tools to "
                "view your cards, check equity, and place your action. "
                "Always call place_action to make your move."
            ),
            show_tool_calls=False,
            markdown=False,
        )
        self._toolkit = toolkit
        self._last_response: str | None = None

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        prompt = user_msgs[-1] if user_msgs else "Make your poker decision."

        response = await self._agent.arun(prompt)

        self._last_response = response.content if response else None

        return {
            "content": self._last_response,
            "tool_calls": [],
        }
