"""Test poker agent with Claude Haiku via the official Anthropic SDK.

Requires: ANTHROPIC_API_KEY environment variable
          pip install anthropic

Usage: uv run python examples/llm-integration-tests/test_anthropic_sdk.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("SKIP: ANTHROPIC_API_KEY not set")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.llm import LLMPlayer  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from providers.anthropic_adapter import AnthropicAdapter  # noqa: E402

NUM_HANDS = 3


async def main() -> None:
    print("Anthropic SDK Test — Claude Haiku vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    adapter = AnthropicAdapter(model="claude-haiku-4-5-20251001")
    engine = PokerEngine(["Claude-Haiku", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "Claude-Haiku")

    llm_player = LLMPlayer(
        name="Claude-Haiku",
        adapter=adapter,
        toolkit=toolkit,
        provider_format="anthropic",
        personality="strategic and calculating",
    )
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"Claude-Haiku": llm_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
