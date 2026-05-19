"""Reddit demo — LFM 2.5 (local) vs GPT-OSS & Kimi (Fireworks cloud)."""

import asyncio
import os
import random
import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# Load .env from parent workspace
env_path = Path(__file__).resolve().parent.parent.parent / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

import openai

from poker_engine.tournament.blind_schedule import BlindLevel, BlindSchedule
from poker_engine.tournament.director import TournamentDirector
from poker_engine.tui.app import PokerTUI

FIREWORKS_BASE = "https://api.fireworks.ai/inference/v1"
FIREWORKS_KEY = os.environ.get("FIREWORKS_API_KEY", "")
LMSTUDIO_BASE = "http://localhost:1234/v1"

PERSONALITIES = {
    "LFM-2.5": (
        "You are a fearless, aggressive poker player. You love to raise and put "
        "pressure on opponents. You rarely fold — you'd rather go down fighting. "
        "Trust your gut over the math."
    ),
    "GPT-OSS": (
        "You are a calculating, analytical poker player. You think about pot odds, "
        "hand ranges, and expected value. You're not afraid to make big laydowns "
        "when the math says fold."
    ),
    "Kimi": (
        "You are a creative, unpredictable poker player. You mix up your play — "
        "sometimes tight, sometimes loose. You like to read your opponents and "
        "adjust. You enjoy the psychological game."
    ),
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
        prompt = self._prompt(gs, actions)
        try:
            r = await self._client.chat.completions.create(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": (
                        f"{self._personality}\n\n"
                        "Analyze your hand vs the board. Think about what your opponents "
                        "might have. Explain your reasoning in 1-2 sentences, then write "
                        "ONLY the action number on the last line."
                    )},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=200,
                temperature=0.8,
            )
            raw = r.choices[0].message.content or ""
            clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            lines = [l.strip() for l in clean.split("\n") if l.strip()]
            thought_lines = [l for l in lines if not re.match(r"^\d+\.?$", l)]
            self._last_thought = thought_lines[0][:100] if thought_lines else None
            return self._parse(raw, actions)
        except Exception as e:
            self._last_thought = f"(error: {type(e).__name__})"
            return self._fallback(actions)

    async def observe(self, event: dict[str, Any]) -> None:
        pass

    async def get_commentary(self) -> str | None:
        return self._last_thought

    async def get_table_talk(self, gs: dict[str, Any]) -> str | None:
        return None

    def _prompt(self, gs: dict[str, Any], actions: list[dict[str, Any]]) -> str:
        lines = [f"Phase: {gs.get('phase')}", f"Pot: ${gs.get('pot', 0)}"]
        if gs.get("hole_cards"):
            lines.append(f"Your cards: {' '.join(gs['hole_cards'])}")
        if gs.get("community_cards"):
            lines.append(f"Board: {' '.join(gs['community_cards'])}")
        lines.append(f"Your chips: ${gs.get('your_chips', 0)}")
        lines.append(f"Cost to call: ${gs.get('current_bet', 0)}")
        lines.append("\nActions:")
        for i, a in enumerate(actions, 1):
            d = a["action"] + (f" (${a['amount']})" if a.get("amount") else "")
            lines.append(f"  {i}. {d}")
        return "\n".join(lines)

    @staticmethod
    def _parse(raw: str, actions: list[dict[str, Any]]) -> dict[str, Any]:
        text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        for line in reversed(text.split("\n")):
            m = re.search(r"\b(\d+)\b", line)
            if m:
                idx = int(m.group(1)) - 1
                if 0 <= idx < len(actions):
                    return actions[idx]
        return LLMPokerPlayer._fallback(actions)

    @staticmethod
    def _fallback(actions: list[dict[str, Any]]) -> dict[str, Any]:
        for a in actions:
            if a["action"] in ("check", "call"):
                return a
        return actions[0] if actions else {"action": "fold"}


async def main():
    if not FIREWORKS_KEY:
        print("ERROR: FIREWORKS_API_KEY not found in .env")
        sys.exit(1)

    players = [
        LLMPokerPlayer("LFM-2.5", "liquid/lfm2.5-1.2b", LMSTUDIO_BASE, "not-needed"),
        LLMPokerPlayer("GPT-OSS", "accounts/fireworks/models/gpt-oss-120b", FIREWORKS_BASE, FIREWORKS_KEY),
        LLMPokerPlayer("Kimi", "accounts/fireworks/models/kimi-k2p5", FIREWORKS_BASE, FIREWORKS_KEY),
    ]

    schedule = BlindSchedule([
        BlindLevel(1, 5, 10, 0, 8),
        BlindLevel(2, 10, 20, 0, 8),
        BlindLevel(3, 25, 50, 5, 8),
    ])

    director = TournamentDirector(
        players=players,
        blind_schedule=schedule,
        starting_chips=500,
        seed=None,
        max_hands=8,
        hand_delay=1.5,
        phase_delay=0.0,
        action_delay=0.3,
        table_talk=True,
    )

    tui = PokerTUI(director)
    result = await tui.run()

    print(f"\nTournament complete! {result.hands_played} hands.")
    for i, s in enumerate(result.standings, 1):
        print(f"  #{i} {s['name']}: ${s['chips']:,}")


if __name__ == "__main__":
    asyncio.run(main())
