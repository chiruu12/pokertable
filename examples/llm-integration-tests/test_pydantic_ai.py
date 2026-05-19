"""Test poker agent via PydanticAI framework.

PydanticAI uses typed dependency injection and structured tool definitions.
The agent gets PokerToolkit as a dependency and calls tools with RunContext.

Requires: ANTHROPIC_API_KEY environment variable
          pip install pydantic-ai

Usage: uv run python examples/llm-integration-tests/test_pydantic_ai.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("SKIP: ANTHROPIC_API_KEY not set")
    sys.exit(0)

try:
    import pydantic_ai  # noqa: F401
except ImportError:
    print("SKIP: pydantic-ai not installed — pip install pydantic-ai")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from frameworks.pydantic_ai_adapter import PydanticAIAdapter  # noqa: E402

NUM_HANDS = 3


class PydanticAIPlayer:
    """Wraps PydanticAIAdapter into a player."""

    def __init__(self, name: str, adapter: PydanticAIAdapter) -> None:
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
            f"Cards: {game_state.get('hole_cards')}. "
            f"Valid: {actions_str}. Use tools to decide."
        )


async def main() -> None:
    print("PydanticAI Framework Test — Claude Haiku (via PydanticAI) vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    engine = PokerEngine(["PydanticAI-Claude", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "PydanticAI-Claude")

    adapter = PydanticAIAdapter(toolkit=toolkit)
    pai_player = PydanticAIPlayer("PydanticAI-Claude", adapter)
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"PydanticAI-Claude": pai_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)


if __name__ == "__main__":
    asyncio.run(main())
