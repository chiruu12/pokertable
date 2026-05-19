"""CrewAI framework adapter — uses CrewAI Agent with custom tools.

CrewAI agents use LangChain-style tools under the hood. We convert poker
ToolDefs into CrewAI-compatible tools and let the agent run its loop.

Requires: pip install crewai
"""

from __future__ import annotations

import json
from typing import Any

from crewai import Agent as CrewAgent
from crewai import Task as CrewTask
from crewai.tools import BaseTool


def make_crewai_tools(toolkit: Any) -> list[BaseTool]:
    """Convert PokerToolkit into CrewAI BaseTool instances."""

    class ViewHandTool(BaseTool):
        name: str = "view_hand"
        description: str = "View your hole cards and current hand strength."

        def _run(self) -> str:
            return json.dumps(toolkit.view_hand())

    class ViewTableTool(BaseTool):
        name: str = "view_table"
        description: str = "View community cards, pot, current bet, and game phase."

        def _run(self) -> str:
            return json.dumps(toolkit.view_table())

    class CheckEquityTool(BaseTool):
        name: str = "check_equity"
        description: str = "Calculate win probability. Pass num_simulations (100-2000)."

        def _run(self, num_simulations: int = 500) -> str:
            return json.dumps(toolkit.check_equity(num_simulations=int(num_simulations)))

    class ViewOpponentsTool(BaseTool):
        name: str = "view_opponents"
        description: str = "View public info about opponents: chips, stats, position."

        def _run(self) -> str:
            return json.dumps(toolkit.view_opponents())

    class PlaceActionTool(BaseTool):
        name: str = "place_action"
        description: str = (
            "Place your poker action. "
            "action: fold/check/call/raise/all_in. "
            "amount: required for raise (the total bet to raise TO)."
        )

        def _run(self, action: str, amount: int = 0) -> str:
            return json.dumps(toolkit.place_action(action=action, amount=int(amount)))

    return [
        ViewHandTool(),
        ViewTableTool(),
        CheckEquityTool(),
        ViewOpponentsTool(),
        PlaceActionTool(),
    ]


class CrewAIAdapter:
    """Adapter that uses a CrewAI Agent as an LLMAdapter."""

    def __init__(
        self,
        toolkit: Any,
        model: str = "anthropic/claude-haiku-4-5-20251001",
    ) -> None:
        crewai_tools = make_crewai_tools(toolkit)

        self._agent = CrewAgent(
            role="Professional poker player",
            goal="Win the poker tournament by making strategic decisions",
            backstory="You are a skilled poker player. Use tools to check "
            "your cards, evaluate equity, and place your action.",
            tools=crewai_tools,
            llm=model,
            verbose=False,
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

        task = CrewTask(
            description=prompt,
            expected_output="A poker action (fold, check, call, raise, or all_in)",
            agent=self._agent,
        )

        result = task.execute_sync()
        self._last_response = str(result) if result else None

        return {
            "content": self._last_response,
            "tool_calls": [],
        }
