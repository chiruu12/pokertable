"""Test poker agent with OpenAI GPT models via the official openai SDK.

Requires: OPENAI_API_KEY environment variable
          pip install openai

Usage: uv run python examples/llm-integration-tests/test_openai_sdk.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("OPENAI_API_KEY"):
    print("SKIP: OPENAI_API_KEY not set")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.llm import LLMPlayer  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from providers.openai_adapter import OpenAIAdapter  # noqa: E402

NUM_HANDS = 3


async def main() -> None:
    print("OpenAI SDK Test — GPT-4o-mini vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    adapter = OpenAIAdapter(model="gpt-4o-mini")
    engine = PokerEngine(["GPT-4o-mini", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "GPT-4o-mini")

    llm_player = LLMPlayer(
        name="GPT-4o-mini",
        adapter=adapter,
        toolkit=toolkit,
        provider_format="openai",
        personality="aggressive bluffer",
    )
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"GPT-4o-mini": llm_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
