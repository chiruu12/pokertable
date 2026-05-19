"""Smolagents (HuggingFace) framework adapter.

Smolagents is a lightweight agent framework from HuggingFace that supports
tool-calling with various LLM backends.

Requires: pip install smolagents
"""

from __future__ import annotations

import json
from typing import Any

from smolagents import CodeAgent, Tool, LiteLLMModel


def make_smolagent_tools(toolkit: Any) -> list[Tool]:
    """Convert PokerToolkit into Smolagents Tool instances."""

    class ViewHandTool(Tool):
        name = "view_hand"
        description = "View your hole cards and current hand strength."
        inputs = {}
        output_type = "string"

        def forward(self) -> str:
            return json.dumps(toolkit.view_hand())

    class ViewTableTool(Tool):
        name = "view_table"
        description = "View community cards, pot, current bet, and game phase."
        inputs = {}
        output_type = "string"

        def forward(self) -> str:
            return json.dumps(toolkit.view_table())

    class CheckEquityTool(Tool):
        name = "check_equity"
        description = "Calculate win probability. num_simulations: 100-2000."
        inputs = {"num_simulations": {"type": "integer", "description": "Simulations to run"}}
        output_type = "string"

        def forward(self, num_simulations: int = 500) -> str:
            return json.dumps(toolkit.check_equity(num_simulations=int(num_simulations)))

    class ViewOpponentsTool(Tool):
        name = "view_opponents"
        description = "View public info about opponents: chips, stats, position."
        inputs = {}
        output_type = "string"

        def forward(self) -> str:
            return json.dumps(toolkit.view_opponents())

    class PlaceActionTool(Tool):
        name = "place_action"
        description = "Place action: fold/check/call/raise/all_in. amount for raise."
        inputs = {
            "action": {"type": "string", "description": "fold, check, call, raise, or all_in"},
            "amount": {"type": "integer", "description": "Raise amount (total bet to raise TO)"},
        }
        output_type = "string"

        def forward(self, action: str, amount: int = 0) -> str:
            return json.dumps(toolkit.place_action(action=action, amount=int(amount)))

    return [
        ViewHandTool(),
        ViewTableTool(),
        CheckEquityTool(),
        ViewOpponentsTool(),
        PlaceActionTool(),
    ]


class SmolagentsAdapter:
    """Adapter that wraps a Smolagents CodeAgent as an LLMAdapter."""

    def __init__(
        self,
        toolkit: Any,
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> None:
        smol_tools = make_smolagent_tools(toolkit)
        llm = LiteLLMModel(model_id=model)

        self._agent = CodeAgent(
            tools=smol_tools,
            model=llm,
        )
        self._last_response: str | None = None

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        user_msgs = [m["content"] for m in messages if m.get("role") == "user"]
        prompt = user_msgs[-1] if user_msgs else "Make your poker decision."

        result = self._agent.run(prompt)
        self._last_response = str(result) if result else None

        return {
            "content": self._last_response,
            "tool_calls": [],
        }
