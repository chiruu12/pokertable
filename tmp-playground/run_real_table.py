"""Reddit demo — console view. LFM 2.5 (local) vs GPT-OSS & Kimi (Fireworks)."""

import asyncio
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import openai
from rich.console import Console

from poker_engine.tournament.blind_schedule import BlindLevel, BlindSchedule
from poker_engine.tournament.director import TournamentDirector
from poker_engine.tui.console_display import ConsoleDisplay

console = Console()
FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
FIREWORKS_KEY = os.environ.get("FIREWORKS_API_KEY", "")
LMSTUDIO_BASE = "http://localhost:1234/v1"

PERSONALITIES = {
    "LFM-2.5": "You are a fearless, aggressive poker player. You raise often and rarely fold.",
    "GPT-OSS": "You are analytical. You think about pot odds and expected value.",
    "Kimi": "You are creative and unpredictable. You mix up your play style.",
}


class LLMPokerPlayer:
    def __init__(self, name: str, model_id: str, base_url: str, api_key: str) -> None:
        self._name = name
        self._model_id = model_id
        self._personality = PERSONALITIES.get(name, "You are a poker player.")
        self._client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)
        self._last_thought: str | None = None
        self._rng = random.Random(hash(name))

    @property
    def name(self) -> str:
        return self._name

    async def decide(self, gs: dict[str, Any], actions: list[dict[str, Any]]) -> dict[str, Any]:
        lines = [f"Phase: {gs.get('phase')}", f"Pot: ${gs.get('pot', 0)}"]
        if gs.get("hole_cards"):
            lines.append(f"Your cards: {' '.join(gs['hole_cards'])}")
        if gs.get("community_cards"):
            lines.append(f"Board: {' '.join(gs['community_cards'])}")
        lines.append(f"Chips: ${gs.get('your_chips', 0)}")
        lines.append("\nActions:")
        for i, a in enumerate(actions, 1):
            d = a["action"] + (f" (${a['amount']})" if a.get("amount") else "")
            lines.append(f"  {i}. {d}")
        prompt = "\n".join(lines)

        try:
            r = await self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": (
                        f"{self._personality}\n"
                        "Explain your reasoning in 1-2 sentences, then write the action number."
                    )},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.8,
            )
            raw = r.choices[0].message.content or ""
            clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            thought_lines = [l.strip() for l in clean.split("\n") if l.strip() and not re.match(r"^\d+\.?$", l)]
            self._last_thought = thought_lines[0][:100] if thought_lines else None

            for line in reversed(clean.split("\n")):
                m = re.search(r"\b(\d+)\b", line)
                if m:
                    idx = int(m.group(1)) - 1
                    if 0 <= idx < len(actions):
                        return actions[idx]
        except Exception as e:
            self._last_thought = f"(error: {type(e).__name__})"

        for a in actions:
            if a["action"] in ("check", "call"):
                return a
        return actions[0] if actions else {"action": "fold"}

    async def observe(self, event: dict[str, Any]) -> None:
        pass

    async def get_commentary(self) -> str | None:
        return self._last_thought

    async def get_table_talk(self, gs: dict[str, Any]) -> str | None:
        return None


async def main():
    if not FIREWORKS_KEY:
        print("ERROR: FIREWORKS_API_KEY not found")
        sys.exit(1)

    console.rule("[bold cyan]LFM-2.5 vs GPT-OSS vs Kimi — Console View[/bold cyan]")
    console.print("  [cyan]LFM-2.5[/cyan] → local (LM Studio)")
    console.print("  [cyan]GPT-OSS[/cyan] → Fireworks (120B)")
    console.print("  [cyan]Kimi[/cyan]    → Fireworks (K2)")

    players = [
        LLMPokerPlayer("LFM-2.5", "liquid/lfm2.5-1.2b", LMSTUDIO_BASE, "not-needed"),
        LLMPokerPlayer("GPT-OSS", "accounts/fireworks/models/gpt-oss-120b", FIREWORKS_BASE, FIREWORKS_KEY),
        LLMPokerPlayer("Kimi", "accounts/fireworks/models/kimi-k2p5", FIREWORKS_BASE, FIREWORKS_KEY),
    ]

    schedule = BlindSchedule([
        BlindLevel(1, 5, 10, 0, 8),
        BlindLevel(2, 10, 20, 0, 8),
    ])

    director = TournamentDirector(
        players=players,
        blind_schedule=schedule,
        starting_chips=500,
        seed=None,
        max_hands=8,
        table_talk=True,
    )

    display = ConsoleDisplay(director, console=console)
    await display.run()


if __name__ == "__main__":
    asyncio.run(main())
