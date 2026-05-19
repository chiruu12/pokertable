"""Table management — seating, balancing, multi-table support."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from poker_engine.core.engine import PokerEngine


@dataclass
class TableSeat:
    player_name: str
    player: Any


@dataclass
class Table:
    table_id: int
    engine: PokerEngine
    seats: list[TableSeat] = field(default_factory=list)

    @property
    def players(self) -> dict[str, Any]:
        return {s.player_name: s.player for s in self.seats}

    @property
    def active_count(self) -> int:
        return len([
            s for s in self.seats
            if any(p.chips > 0 for p in self.engine.players if p.name == s.player_name)
        ])


class TableManager:
    """Manages seating and table balancing for single or multi-table play."""

    def __init__(self, max_per_table: int = 9) -> None:
        self._max_per_table = max_per_table
        self._tables: list[Table] = []
        self._eliminated: list[str] = []

    def seat_players(
        self,
        players: list[Any],
        starting_chips: int = 1000,
        seed: int | None = None,
    ) -> list[Table]:
        num_tables = max(1, (len(players) + self._max_per_table - 1) // self._max_per_table)
        self._tables = []

        for t_idx in range(num_tables):
            start = t_idx * self._max_per_table
            end = min(start + self._max_per_table, len(players))
            table_players = players[start:end]
            names = [p.name for p in table_players]

            engine = PokerEngine(
                names,
                starting_chips=starting_chips,
                seed=(seed + t_idx) if seed is not None else None,
            )

            seats = [TableSeat(p.name, p) for p in table_players]
            self._tables.append(Table(t_idx, engine, seats))

        return self._tables

    def active_tables(self) -> list[Table]:
        return [t for t in self._tables if t.active_count >= 2]

    def eliminate_busted(self) -> list[str]:
        newly_eliminated = []
        for table in self._tables:
            for seat in table.seats:
                player_state = next(
                    (p for p in table.engine.players if p.name == seat.player_name),
                    None,
                )
                if (
                    player_state
                    and player_state.chips <= 0
                    and seat.player_name not in self._eliminated
                ):
                    self._eliminated.append(seat.player_name)
                    newly_eliminated.append(seat.player_name)
        return newly_eliminated

    def rebalance(self) -> None:
        active = self.active_tables()
        if len(active) <= 1:
            return
        # For now, single-table only — multi-table balancing is future work

    @property
    def tables(self) -> list[Table]:
        return list(self._tables)

    @property
    def eliminated(self) -> list[str]:
        return list(self._eliminated)
