"""Test poker agent with a local LM Studio model.

Requires: LM Studio running with a model loaded (e.g. LFM, Llama, Mistral)
          pip install openai

Set LMSTUDIO_BASE_URL if not using default http://localhost:1234/v1

Usage: uv run python examples/llm-integration-tests/test_lmstudio.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

BASE_URL = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")

try:
    resp = httpx.get(f"{BASE_URL}/models", timeout=3)
    resp.raise_for_status()
    models = resp.json().get("data", [])
    if not models:
        print("SKIP: LM Studio running but no model loaded")
        sys.exit(0)
    MODEL_ID = models[0]["id"]
    print(f"Detected LM Studio model: {MODEL_ID}")
except Exception:
    print(f"SKIP: LM Studio not reachable at {BASE_URL}")
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
    print(f"\nLM Studio Test — {MODEL_ID} vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    adapter = OpenAIAdapter(
        model=MODEL_ID,
        base_url=BASE_URL,
        api_key="not-needed",
    )
    engine = PokerEngine(["LocalLLM", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "LocalLLM")

    llm_player = LLMPlayer(
        name="LocalLLM",
        adapter=adapter,
        toolkit=toolkit,
        provider_format="openai",
    )
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"LocalLLM": llm_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)
    await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
