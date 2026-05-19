"""Mixed provider tournament — different LLM providers compete.

Detects available providers and creates a tournament with 2+ LLM players
plus a random baseline.

Requires: At least 1 of ANTHROPIC_API_KEY, OPENAI_API_KEY, FIREWORKS_API_KEY,
          or LM Studio running locally.
          pip install anthropic openai

Usage: uv run python examples/llm-integration-tests/test_multi_provider.py
"""

from __future__ import annotations

import asyncio
import os
import sys

from helpers import REPO_ROOT, print_final_standings, run_hand  # noqa: E402

sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import PokerEngine  # noqa: E402
from poker_engine.players.llm import LLMPlayer  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402

NUM_HANDS = 5


def detect_providers() -> list[tuple[str, object, str]]:
    """Detect available providers. Returns (name, adapter, format) tuples."""
    available = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from providers.anthropic_adapter import AnthropicAdapter

            adapter = AnthropicAdapter(model="claude-haiku-4-5-20251001")
            available.append(("Claude-Haiku", adapter, "anthropic"))
            print("  Found: Anthropic (Claude Haiku)")
        except Exception as e:
            print(f"  Anthropic init failed: {e}")

    if os.environ.get("OPENAI_API_KEY"):
        try:
            from providers.openai_adapter import OpenAIAdapter

            adapter = OpenAIAdapter(model="gpt-4o-mini")
            available.append(("GPT-4o-mini", adapter, "openai"))
            print("  Found: OpenAI (GPT-4o-mini)")
        except Exception as e:
            print(f"  OpenAI init failed: {e}")

    if os.environ.get("FIREWORKS_API_KEY"):
        try:
            from providers.openai_adapter import OpenAIAdapter

            adapter = OpenAIAdapter(
                model="accounts/fireworks/models/llama-v3p1-8b-instruct",
                base_url="https://api.fireworks.ai/inference/v1",
                api_key=os.environ["FIREWORKS_API_KEY"],
            )
            available.append(("Llama-3.1-FW", adapter, "openai"))
            print("  Found: Fireworks (Llama 3.1)")
        except Exception as e:
            print(f"  Fireworks init failed: {e}")

    try:
        import httpx

        base = os.environ.get("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        resp = httpx.get(f"{base}/models", timeout=2)
        if resp.status_code == 200:
            from providers.openai_adapter import OpenAIAdapter

            models = resp.json().get("data", [])
            if models:
                model_id = models[0]["id"]
                adapter = OpenAIAdapter(model=model_id, base_url=base, api_key="not-needed")
                available.append(("LocalLLM", adapter, "openai"))
                print(f"  Found: LM Studio ({model_id})")
    except Exception:
        pass

    return available


async def main() -> None:
    print("Detecting available providers...")
    providers = detect_providers()

    if len(providers) < 1:
        print("\nSKIP: No LLM providers available")
        sys.exit(0)

    all_names = [name for name, _, _ in providers] + ["RandomBot"]
    print(f"\nMulti-Provider Tournament: {', '.join(all_names)}")
    print(f"Playing {NUM_HANDS} hands\n")

    engine = PokerEngine(all_names, starting_chips=500, seed=42)

    players: dict[str, object] = {}
    for name, adapter, fmt in providers:
        toolkit = PokerToolkit(engine, name)
        players[name] = LLMPlayer(
            name=name,
            adapter=adapter,
            toolkit=toolkit,
            provider_format=fmt,
        )
    players["RandomBot"] = RandomPlayer("RandomBot", seed=1)

    for i in range(1, NUM_HANDS + 1):
        await run_hand(engine, players, i)

    print_final_standings(engine)

    for _, adapter, _ in providers:
        if hasattr(adapter, "close"):
            await adapter.close()


if __name__ == "__main__":
    asyncio.run(main())
