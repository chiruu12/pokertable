"""BasePlayer protocol — the interface all player types implement."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BasePlayer(Protocol):
    """Protocol that all player implementations must satisfy."""

    @property
    def name(self) -> str: ...

    async def decide(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Choose an action given the game state.

        Args:
            game_state: Public game info (pot, community, phase, etc.)
            valid_actions: List of valid actions with amounts.

        Returns:
            {"action": "call"} or {"action": "raise", "amount": 100} etc.
        """
        ...

    async def observe(self, event: dict[str, Any]) -> None:
        """Called when something happens in the game."""
        ...

    async def get_commentary(self) -> str | None:
        """Optional: return a comment or reasoning string for TUI display."""
        ...
