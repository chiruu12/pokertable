"""Test poker agent via Agno framework.

Agno (formerly Phidata) manages its own tool-calling loop. We register
poker tools as Agno-native tools and let the agent reason about the game.

Requires: ANTHROPIC_API_KEY environment variable
          pip install agno

Usage: uv run python examples/llm-integration-tests/test_agno.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("SKIP: ANTHROPIC_API_KEY not set")
    sys.exit(0)

try:
    import agno  # noqa: F401
except ImportError:
    print("SKIP: agno not installed — pip install agno")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from frameworks.agno_adapter import AgnoAdapter  # noqa: E402

NUM_HANDS = 3


class AgnoPlayer:
    """Wraps AgnoAdapter into a player that conforms to BasePlayer."""

    def __init__(self, name: str, adapter: AgnoAdapter) -> None:
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
            f"Your cards: {game_state.get('hole_cards')}. "
            f"Valid actions: {actions_str}. "
            f"Use the tools to view your hand, check equity, and place your action."
        )


async def main() -> None:
    print("Agno Framework Test — Claude Haiku (via Agno) vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    engine = PokerEngine(["Agno-Claude", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "Agno-Claude")

    adapter = AgnoAdapter(toolkit=toolkit, model="claude-haiku-4-5-20251001")
    agno_player = AgnoPlayer("Agno-Claude", adapter)
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"Agno-Claude": agno_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)


if __name__ == "__main__":
    asyncio.run(main())
