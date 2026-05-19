"""Human player — prompts for input via stdin."""

from __future__ import annotations

import asyncio
from typing import Any


class HumanPlayer:
    """Interactive CLI player that reads actions from stdin."""

    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def decide(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        print(f"\n--- {self._name}'s turn ---")
        print(f"Phase: {game_state.get('phase', '?')}")
        print(f"Pot: {game_state.get('pot', 0)}")
        if game_state.get("community_cards"):
            print(f"Community: {' '.join(game_state['community_cards'])}")
        if game_state.get("hole_cards"):
            print(f"Your cards: {' '.join(game_state['hole_cards'])}")

        print("\nValid actions:")
        for i, action in enumerate(valid_actions, 1):
            desc = action["action"]
            if action.get("amount"):
                desc += f" ({action['amount']})"
            print(f"  {i}. {desc}")

        while True:
            raw = await asyncio.to_thread(
                input, f"Choose action (1-{len(valid_actions)}): "
            )
            try:
                idx = int(raw.strip()) - 1
                if 0 <= idx < len(valid_actions):
                    return valid_actions[idx]
            except ValueError:
                pass
            print("Invalid choice, try again.")

    async def observe(self, event: dict[str, Any]) -> None:
        event_type = event.get("type", "unknown")
        if event_type == "player_action":
            player = event.get("player", "?")
            action = event.get("action", "?")
            amount = event.get("amount", "")
            suffix = f" ({amount})" if amount else ""
            print(f"  {player}: {action}{suffix}")

    async def get_commentary(self) -> str | None:
        return None
