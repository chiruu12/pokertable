"""Tournament event types and pub/sub event bus."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class TournamentEvent:
    event_type: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass(frozen=True)
class HandStartEvent(TournamentEvent):
    event_type: str = "hand_start"
    hand_num: int = 0
    dealer: str = ""


@dataclass(frozen=True)
class PhaseChangeEvent(TournamentEvent):
    event_type: str = "phase_change"
    phase: str = ""
    community: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ActionEvent(TournamentEvent):
    event_type: str = "action"
    player: str = ""
    action: str = ""
    amount: int = 0
    pot: int = 0


@dataclass(frozen=True)
class CommentaryEvent(TournamentEvent):
    event_type: str = "commentary"
    player: str = ""
    text: str = ""


@dataclass(frozen=True)
class HandEndEvent(TournamentEvent):
    event_type: str = "hand_end"
    hand_num: int = 0
    winners: list[str] = field(default_factory=list)
    win_reason: str = ""


@dataclass(frozen=True)
class BlindLevelEvent(TournamentEvent):
    event_type: str = "blind_level"
    level: int = 0
    small_blind: int = 0
    big_blind: int = 0
    ante: int = 0


@dataclass(frozen=True)
class EliminationEvent(TournamentEvent):
    event_type: str = "elimination"
    player: str = ""
    position: int = 0


class EventBus:
    """Simple pub/sub for tournament events."""

    def __init__(self) -> None:
        self._subscribers: list[Callable[[TournamentEvent], Any]] = []
        self._history: list[TournamentEvent] = []

    def subscribe(self, callback: Callable[[TournamentEvent], Any]) -> None:
        self._subscribers.append(callback)

    def emit(self, event: TournamentEvent) -> None:
        self._history.append(event)
        for cb in self._subscribers:
            cb(event)

    def get_history(self) -> list[TournamentEvent]:
        return list(self._history)

    def clear(self) -> None:
        self._history.clear()
