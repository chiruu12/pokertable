"""Hand history recording and JSON export."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from poker_engine.core.engine import HandSummary


@dataclass
class HandRecord:
    hand_num: int
    players: list[dict[str, Any]]
    blinds: tuple[int, int, int]
    actions: list[dict[str, Any]] = field(default_factory=list)
    community: list[str] = field(default_factory=list)
    winners: list[str] = field(default_factory=list)
    win_reason: str = ""

    @classmethod
    def from_summary(
        cls,
        summary: HandSummary,
        player_chips: dict[str, int],
        blind_info: tuple[int, int, int] = (10, 20, 0),
    ) -> HandRecord:
        players = [
            {"name": name, "chips": chips} for name, chips in player_chips.items()
        ]
        community = [str(c) for c in summary.community]
        return cls(
            hand_num=summary.hand_num,
            players=players,
            blinds=blind_info,
            community=community,
            winners=summary.winners,
            win_reason=summary.win_reason,
        )


class HandHistory:
    """Records complete hand histories for replay and export."""

    def __init__(self) -> None:
        self._hands: list[HandRecord] = []

    def record(self, hand: HandRecord) -> None:
        self._hands.append(hand)

    @property
    def hands(self) -> list[HandRecord]:
        return list(self._hands)

    def to_json(self) -> str:
        return json.dumps(
            [asdict(h) for h in self._hands], indent=2, default=str
        )

    def to_file(self, path: str | Path) -> None:
        Path(path).write_text(self.to_json())

    @classmethod
    def from_file(cls, path: str | Path) -> HandHistory:
        data = json.loads(Path(path).read_text())
        history = cls()
        for entry in data:
            history._hands.append(HandRecord(**entry))
        return history
