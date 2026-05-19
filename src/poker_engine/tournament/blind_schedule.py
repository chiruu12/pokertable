"""Blind level progression for tournaments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlindLevel:
    level: int
    small_blind: int
    big_blind: int
    ante: int = 0
    duration_hands: int = 10


class BlindSchedule:
    """Manages blind level progression based on hands played."""

    def __init__(self, levels: list[BlindLevel]) -> None:
        if not levels:
            raise ValueError("At least one blind level required")
        self._levels = levels

    @classmethod
    def turbo(cls) -> BlindSchedule:
        return cls([
            BlindLevel(1, 10, 20, 0, 5),
            BlindLevel(2, 15, 30, 0, 5),
            BlindLevel(3, 25, 50, 5, 5),
            BlindLevel(4, 50, 100, 10, 5),
            BlindLevel(5, 75, 150, 15, 5),
            BlindLevel(6, 100, 200, 25, 5),
            BlindLevel(7, 150, 300, 50, 5),
            BlindLevel(8, 250, 500, 50, 5),
        ])

    @classmethod
    def standard(cls) -> BlindSchedule:
        return cls([
            BlindLevel(1, 10, 20, 0, 10),
            BlindLevel(2, 15, 30, 0, 10),
            BlindLevel(3, 25, 50, 5, 10),
            BlindLevel(4, 50, 100, 10, 10),
            BlindLevel(5, 75, 150, 15, 10),
            BlindLevel(6, 100, 200, 25, 10),
            BlindLevel(7, 150, 300, 50, 10),
            BlindLevel(8, 250, 500, 50, 10),
        ])

    def current_level(self, hands_played: int) -> BlindLevel:
        cumulative = 0
        for level in self._levels:
            cumulative += level.duration_hands
            if hands_played < cumulative:
                return level
        return self._levels[-1]

    @property
    def levels(self) -> list[BlindLevel]:
        return list(self._levels)
