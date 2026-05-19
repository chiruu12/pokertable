"""Scripted player — follows a predetermined action sequence. For testing."""

from __future__ import annotations

from typing import Any


class ScriptedPlayer:
    """Plays a predetermined sequence of actions. Loops if script exhausted."""

    def __init__(self, name: str, script: list[dict[str, Any]]) -> None:
        self._name = name
        self._script = script
        self._index = 0
        self._events: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return self._name

    async def decide(
        self,
        game_state: dict[str, Any],
        valid_actions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        if not self._script:
            return valid_actions[0] if valid_actions else {"action": "fold"}

        action = self._script[self._index % len(self._script)]
        self._index += 1
        return action

    async def observe(self, event: dict[str, Any]) -> None:
        self._events.append(event)

    async def get_commentary(self) -> str | None:
        return None
