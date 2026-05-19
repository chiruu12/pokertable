"""Tests for TableManager — seating, balancing, elimination."""

from __future__ import annotations

from poker_engine.tournament.table_manager import TableManager

# ── Lightweight player stand-in ──────────────────────────────────────


class _Stub:
    """Minimal player-like object with a .name attribute."""

    def __init__(self, name: str) -> None:
        self.name = name


def _stubs(n: int) -> list[_Stub]:
    return [_Stub(f"P{i}") for i in range(n)]


# ── seat_players ─────────────────────────────────────────────────────


def test_seat_3_players_one_table():
    tm = TableManager(max_per_table=9)
    tables = tm.seat_players(_stubs(3))
    assert len(tables) == 1
    assert len(tables[0].seats) == 3


def test_seat_10_players_two_tables():
    tm = TableManager(max_per_table=6)
    tables = tm.seat_players(_stubs(10))
    assert len(tables) == 2
    assert len(tables[0].seats) == 6
    assert len(tables[1].seats) == 4


def test_seat_players_custom_starting_chips():
    tm = TableManager()
    tables = tm.seat_players(_stubs(2), starting_chips=5000)
    for p in tables[0].engine.players:
        assert p.chips == 5000


def test_seed_propagation():
    tm = TableManager(max_per_table=3)
    tables = tm.seat_players(_stubs(6), seed=100)
    # Table 0 gets seed 100, table 1 gets seed 101 — both deterministic.
    # Just verify they got created with 2 tables and are playable.
    assert len(tables) == 2
    tables[0].engine.new_hand()
    tables[1].engine.new_hand()
    # Different seeds should (almost certainly) produce different deals.
    cards0 = [str(c) for p in tables[0].engine.players for c in p.hole_cards]
    cards1 = [str(c) for p in tables[1].engine.players for c in p.hole_cards]
    assert cards0 != cards1


# ── Table properties ─────────────────────────────────────────────────


def test_table_players_dict():
    tm = TableManager()
    stubs = _stubs(3)
    tables = tm.seat_players(stubs)
    players = tables[0].players
    assert isinstance(players, dict)
    assert set(players.keys()) == {"P0", "P1", "P2"}


def test_table_active_count_all_alive():
    tm = TableManager()
    tables = tm.seat_players(_stubs(3), starting_chips=500)
    tables[0].engine.new_hand()
    assert tables[0].active_count == 3


def test_table_active_count_after_bust():
    tm = TableManager()
    tables = tm.seat_players(_stubs(3), starting_chips=500)
    # Bust one player
    tables[0].engine.players[0].chips = 0
    assert tables[0].active_count == 2


# ── active_tables ────────────────────────────────────────────────────


def test_active_tables_excludes_busted_table():
    tm = TableManager()
    tables = tm.seat_players(_stubs(2), starting_chips=500)
    # Bust all but one — only 1 active, table needs 2+
    tables[0].engine.players[0].chips = 0
    assert len(tm.active_tables()) == 0


def test_active_tables_includes_healthy_table():
    tm = TableManager()
    tm.seat_players(_stubs(3), starting_chips=500)
    assert len(tm.active_tables()) == 1


# ── eliminate_busted ─────────────────────────────────────────────────


def test_eliminate_busted_detects_zero_chips():
    tm = TableManager()
    tables = tm.seat_players(_stubs(3), starting_chips=500)
    tables[0].engine.players[1].chips = 0
    eliminated = tm.eliminate_busted()
    assert "P1" in eliminated


def test_eliminate_busted_no_double_count():
    tm = TableManager()
    tables = tm.seat_players(_stubs(3), starting_chips=500)
    tables[0].engine.players[1].chips = 0
    first = tm.eliminate_busted()
    second = tm.eliminate_busted()
    assert "P1" in first
    assert "P1" not in second
    assert tm.eliminated == ["P1"]


# ── rebalance ────────────────────────────────────────────────────────


def test_rebalance_single_table_noop():
    tm = TableManager()
    tm.seat_players(_stubs(3))
    # Should not raise or change anything.
    tm.rebalance()
    assert len(tm.tables) == 1
