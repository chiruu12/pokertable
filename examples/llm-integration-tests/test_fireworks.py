"""Test poker agent with Fireworks AI OSS models via OpenAI-compatible SDK.

Requires: FIREWORKS_API_KEY environment variable
          pip install openai

Uses: Llama 3.1 8B Instruct (or whichever model you prefer)

Usage: uv run python examples/llm-integration-tests/test_fireworks.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("FIREWORKS_API_KEY"):
    print("SKIP: FIREWORKS_API_KEY not set")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.llm import LLMPlayer  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from providers.openai_adapter import OpenAIAdapter  # noqa: E402

NUM_HANDS = 3
FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
FIREWORKS_MODEL = "accounts/fireworks/models/llama-v3p1-8b-instruct"


async def main() -> None:
    print(f"Fireworks AI Test — {FIREWORKS_MODEL.split('/')[-1]} vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    adapter = OpenAIAdapter(
        model=FIREWORKS_MODEL,
        base_url=FIREWORKS_BASE,
        api_key=os.environ["FIREWORKS_API_KEY"],
    )
    engine = PokerEngine(["Llama-3.1", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "Llama-3.1")

    llm_player = LLMPlayer(
        name="Llama-3.1",
        adapter=adapter,
        toolkit=toolkit,
        provider_format="openai",
        personality="tight and methodical",
    )
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"Llama-3.1": llm_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
