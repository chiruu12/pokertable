"""Payout structures for tournaments."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PayoutStructure:
    """Defines prize distribution as percentages of the total prize pool."""

    name: str
    percentages: list[float]

    @classmethod
    def winner_take_all(cls) -> PayoutStructure:
        return cls("Winner Take All", [1.0])

    @classmethod
    def top_2(cls) -> PayoutStructure:
        return cls("Top 2", [0.65, 0.35])

    @classmethod
    def top_3(cls) -> PayoutStructure:
        return cls("Top 3", [0.50, 0.30, 0.20])

    @classmethod
    def default(cls, num_players: int) -> PayoutStructure:
        if num_players <= 2:
            return cls.winner_take_all()
        if num_players <= 4:
            return cls.top_2()
        return cls.top_3()

    def calculate(self, prize_pool: int) -> list[int]:
        """Return payout amounts for each place."""
        payouts = [int(prize_pool * pct) for pct in self.percentages]
        remainder = prize_pool - sum(payouts)
        if remainder > 0 and payouts:
            payouts[0] += remainder
        return payouts
