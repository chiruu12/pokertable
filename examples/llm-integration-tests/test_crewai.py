"""Test poker agent via CrewAI framework.

CrewAI creates role-based agents with tools. We give it poker tools
and a "professional poker player" role.

Requires: ANTHROPIC_API_KEY or OPENAI_API_KEY environment variable
          pip install crewai

Usage: uv run python examples/llm-integration-tests/test_crewai.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("OPENAI_API_KEY")):
    print("SKIP: Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY set")
    sys.exit(0)

try:
    import crewai  # noqa: F401
except ImportError:
    print("SKIP: crewai not installed — pip install crewai")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from frameworks.crewai_adapter import CrewAIAdapter  # noqa: E402

NUM_HANDS = 3


class CrewAIPlayer:
    """Wraps CrewAIAdapter into a player."""

    def __init__(self, name: str, adapter: CrewAIAdapter) -> None:
        self._name = name
        self._adapter = adapter
        self._last_commentary: str | None = None

    @property
    def name(self) -> str:
        return self._name

    async def decide(self, game_state, valid_actions):
        result = await self._adapter.generate(
            messages=[{"role": "user", "content": self._build_prompt(game_state, valid_actions)}],
            tools=[],
        )
        self._last_commentary = result.get("content")
        for a in valid_actions:
            if a["action"] in ("check", "call"):
                return a
        return valid_actions[0] if valid_actions else {"action": "fold"}

    async def observe(self, event):
        pass

    async def get_commentary(self):
        return self._last_commentary

    @staticmethod
    def _build_prompt(game_state, valid_actions):
        actions_str = ", ".join(a["action"] for a in valid_actions)
        return (
            f"Phase: {game_state.get('phase')}. Pot: {game_state.get('pot')}. "
            f"Valid actions: {actions_str}. Use tools to decide, then place_action."
        )


async def main() -> None:
    model = "anthropic/claude-haiku-4-5-20251001"
    if not os.environ.get("ANTHROPIC_API_KEY"):
        model = "openai/gpt-4o-mini"

    print(f"CrewAI Framework Test — {model} vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    engine = PokerEngine(["CrewAI-Agent", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "CrewAI-Agent")

    adapter = CrewAIAdapter(toolkit=toolkit, model=model)
    crew_player = CrewAIPlayer("CrewAI-Agent", adapter)
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"CrewAI-Agent": crew_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)


if __name__ == "__main__":
    asyncio.run(main())
