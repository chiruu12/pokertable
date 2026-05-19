"""PydanticAI framework adapter — structured agent with typed tool results.

PydanticAI excels at structured outputs and type-safe tool definitions.
We register poker tools as PydanticAI tools and let the agent reason.

Requires: pip install pydantic-ai
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from pydantic_ai import Agent as PydanticAgent
from pydantic_ai import RunContext


@dataclass
class PokerDeps:
    """Dependencies injected into PydanticAI tool functions."""

    toolkit: Any


def create_pydantic_agent(model: str = "anthropic:claude-haiku-4-5-20251001") -> PydanticAgent:
    """Create a PydanticAI agent with poker tools registered."""

    agent = PydanticAgent(
        model,
        deps_type=PokerDeps,
        system_prompt=(
            "You are playing Texas Hold'em poker. Use the tools to inspect "
            "your hand, check equity, view opponents, and place your action. "
            "You MUST call place_action to make your final decision."
        ),
    )

    @agent.tool
    def view_hand(ctx: RunContext[PokerDeps]) -> str:
        """View your hole cards and current hand strength."""
        return json.dumps(ctx.deps.toolkit.view_hand())

    @agent.tool
    def view_table(ctx: RunContext[PokerDeps]) -> str:
        """View community cards, pot, current bet, and game phase."""
        return json.dumps(ctx.deps.toolkit.view_table())

    @agent.tool
    def check_equity(ctx: RunContext[PokerDeps], num_simulations: int = 500) -> str:
        """Calculate win probability via Monte Carlo simulation."""
        return json.dumps(ctx.deps.toolkit.check_equity(num_simulations=num_simulations))

    @agent.tool
    def view_opponents(ctx: RunContext[PokerDeps]) -> str:
        """View public information about all opponents."""
        return json.dumps(ctx.deps.toolkit.view_opponents())

    @agent.tool
    def place_action(ctx: RunContext[PokerDeps], action: str, amount: int = 0) -> str:
        """Place your poker action: fold, check, call, raise, or all_in."""
        return json.dumps(ctx.deps.toolkit.place_action(action=action, amount=amount))

    return agent


class PydanticAIAdapter:
    """Adapter that wraps a PydanticAI Agent as an LLMAdapter."""

    def __init__(
        self,
        toolkit: Any,
        model: str = "anthropic:claude-haiku-4-5-20251001",
    ) -> None:
        self._agent = create_pydantic_agent(model)
        self._deps = PokerDeps(toolkit=toolkit)
        self._last_response: str | None = None

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        prompt = user_msgs[-1] if user_msgs else "Make your poker decision."

        result = await self._agent.run(prompt, deps=self._deps)
        self._last_response = result.data if result else None

        return {
            "content": str(self._last_response) if self._last_response else None,
            "tool_calls": [],
        }
