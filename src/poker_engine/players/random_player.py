"""Random player — weighted baseline for testing and benchmarks."""

from __future__ import annotations

import random
from typing import Any


class RandomPlayer:
    """Makes random valid moves with configurable aggression weights."""

    def __init__(
        self,
        name: str,
        seed: int | None = None,
        fold_weight: float = 0.15,
        passive_weight: float = 0.60,
        aggressive_weight: float = 0.25,
    ) -> None:
        self._name = name
        self._rng = random.Random(seed)
        self._fold_w = fold_weight
        self._passive_w = passive_weight
        self._aggressive_w = aggressive_weight

    @property
    def name(self) -> str:
        return self._name

    async def decide(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        folds = [a for a in valid_actions if a["action"] == "fold"]
        passive = [a for a in valid_actions if a["action"] in ("check", "call")]
        aggressive = [
            a for a in valid_actions if a["action"] in ("raise", "all_in")
        ]

        buckets = []
        if folds:
            buckets.append((self._fold_w, folds))
        if passive:
            buckets.append((self._passive_w, passive))
        if aggressive:
            buckets.append((self._aggressive_w, aggressive))

        if not buckets:
            return valid_actions[0] if valid_actions else {"action": "fold"}

        weights = [w for w, _ in buckets]
        chosen_bucket = self._rng.choices(
            [acts for _, acts in buckets], weights=weights, k=1
        )[0]
        return self._rng.choice(chosen_bucket)

    async def observe(self, event: dict[str, Any]) -> None:
        pass

    async def get_commentary(self) -> str | None:
        return None
