"""Mixed framework tournament — different agent frameworks compete.

Detects available frameworks and creates a tournament where agents built
on different frameworks (Agno, LangChain, CrewAI, PydanticAI) play against
each other and a random baseline.

Requires: ANTHROPIC_API_KEY environment variable
          At least 1 framework installed (agno, langchain-anthropic, crewai, or pydantic-ai)

Usage: uv run python examples/llm-integration-tests/test_multi_framework.py
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

NUM_HANDS = 5


def _make_framework_player(name, adapter):
    """Wrap a framework adapter that handles its own tool loop."""

    class _FrameworkPlayer:
        def __init__(self):
            self._name = name
            self._adapter = adapter
            self._last_commentary = None

        @property
        def name(self):
            return self._name

        async def decide(self, game_state, valid_actions):
            result = await self._adapter.generate(
                messages=[{
                    "role": "user",
                    "content": (
                        f"Phase: {game_state.get('phase')}. "
                        f"Pot: {game_state.get('pot')}. "
                        f"Cards: {game_state.get('hole_cards')}. "
                        f"Valid: {', '.join(a['action'] for a in valid_actions)}. "
                        "Use tools to decide."
                    ),
                }],
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

    return _FrameworkPlayer()


def detect_frameworks(engine, all_names):
    """Detect available frameworks and create players."""
    available = {}

    if "Agno-Claude" in all_names:
        try:
            import agno  # noqa: F401
            from frameworks.agno_adapter import AgnoAdapter

            toolkit = PokerToolkit(engine, "Agno-Claude")
            adapter = AgnoAdapter(toolkit=toolkit)
            available["Agno-Claude"] = _make_framework_player("Agno-Claude", adapter)
            print("  Found: Agno")
        except Exception as e:
            print(f"  Agno failed: {e}")
            all_names.remove("Agno-Claude")

    if "LC-Claude" in all_names:
        try:
            from langchain_anthropic import ChatAnthropic
            from frameworks.langchain_adapter import LangChainAdapter

            toolkit = PokerToolkit(engine, "LC-Claude")
            chat = ChatAnthropic(model="claude-haiku-4-5-20251001")
            adapter = LangChainAdapter(chat)
            available["LC-Claude"] = LLMPlayer(
                name="LC-Claude", adapter=adapter,
                toolkit=toolkit, provider_format="anthropic",
            )
            print("  Found: LangChain")
        except Exception as e:
            print(f"  LangChain failed: {e}")
            all_names.remove("LC-Claude")

    if "CrewAI-Agent" in all_names:
        try:
            import crewai  # noqa: F401
            from frameworks.crewai_adapter import CrewAIAdapter

            toolkit = PokerToolkit(engine, "CrewAI-Agent")
            adapter = CrewAIAdapter(toolkit=toolkit)
            available["CrewAI-Agent"] = _make_framework_player("CrewAI-Agent", adapter)
            print("  Found: CrewAI")
        except Exception as e:
            print(f"  CrewAI failed: {e}")
            all_names.remove("CrewAI-Agent")

    if "PydAI-Claude" in all_names:
        try:
            import pydantic_ai  # noqa: F401
            from frameworks.pydantic_ai_adapter import PydanticAIAdapter

            toolkit = PokerToolkit(engine, "PydAI-Claude")
            adapter = PydanticAIAdapter(toolkit=toolkit)
            available["PydAI-Claude"] = _make_framework_player("PydAI-Claude", adapter)
            print("  Found: PydanticAI")
        except Exception as e:
            print(f"  PydanticAI failed: {e}")
            all_names.remove("PydAI-Claude")

    return available


async def main() -> None:
    print("Detecting available frameworks...")

    candidate_names = ["Agno-Claude", "LC-Claude", "CrewAI-Agent", "PydAI-Claude", "RandomBot"]
    engine = PokerEngine(candidate_names, starting_chips=500, seed=42)

    framework_players = detect_frameworks(engine, candidate_names)

    if len(framework_players) < 1:
        print("\nSKIP: No agent frameworks available")
        sys.exit(0)

    active_names = list(framework_players.keys()) + ["RandomBot"]

    if len(active_names) < 2:
        print("\nSKIP: Need at least 2 players")
        sys.exit(0)

    engine = PokerEngine(active_names, starting_chips=500, seed=42)
    framework_players_final = detect_frameworks(engine, list(active_names))

    players = {**framework_players_final}
    players["RandomBot"] = RandomPlayer("RandomBot", seed=1)

    print(f"\nMulti-Framework Tournament: {', '.join(active_names)}")
    print(f"Playing {NUM_HANDS} hands\n")

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)


if __name__ == "__main__":
    asyncio.run(main())
