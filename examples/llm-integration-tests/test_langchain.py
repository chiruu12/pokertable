"""Test poker agent via LangChain framework.

Uses LangChain's ChatAnthropic with tool binding. The LangChainAdapter
translates between poker's message format and LangChain's message types.

Requires: ANTHROPIC_API_KEY environment variable
          pip install langchain langchain-anthropic

Usage: uv run python examples/llm-integration-tests/test_langchain.py
"""

from __future__ import annotations

import asyncio
import os
import sys

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("SKIP: ANTHROPIC_API_KEY not set")
    sys.exit(0)

try:
    from langchain_anthropic import ChatAnthropic
except ImportError:
    print("SKIP: langchain-anthropic not installed — pip install langchain-anthropic")
    sys.exit(0)

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.llm import LLMPlayer  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402
from frameworks.langchain_adapter import LangChainAdapter  # noqa: E402

NUM_HANDS = 3


async def main() -> None:
    print("LangChain Framework Test — ChatAnthropic (Haiku) vs Random Bot")
    print(f"Playing {NUM_HANDS} hands\n")

    chat_model = ChatAnthropic(model="claude-haiku-4-5-20251001")
    adapter = LangChainAdapter(chat_model)

    engine = PokerEngine(["LC-Claude", "RandomBot"], starting_chips=500, seed=42)
    toolkit = PokerToolkit(engine, "LC-Claude")

    llm_player = LLMPlayer(
        name="LC-Claude",
        adapter=adapter,
        toolkit=toolkit,
        provider_format="anthropic",
        personality="balanced and analytical",
    )
    random_player = RandomPlayer("RandomBot", seed=1)

    players = {"LC-Claude": llm_player, "RandomBot": random_player}

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)


if __name__ == "__main__":
    asyncio.run(main())
