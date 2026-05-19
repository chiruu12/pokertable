"""Edge-case tests for PokerToolkit tools."""

import pytest

from poker_engine.core.engine import Action, ActionType, PokerEngine
from poker_engine.tools.poker_tools import PokerToolkit

# ── helpers ──────────────────────────────────────────────────────────


def _call_or_check(engine: PokerEngine) -> None:
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        safe = next(
            (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)),
            actions[0],
        )
        engine.apply_action(p.name, safe)


@pytest.fixture
def three_player_game():
    engine = PokerEngine(["Alice", "Bob", "Charlie"], starting_chips=1000, seed=42)
    engine.new_hand()
    return engine


# ── check_equity with 0 opponents ───────────────────────────────────


def test_check_equity_zero_opponents():
    """When everyone else folded, equity should be 1.0."""
    engine = PokerEngine(["Alice", "Bob"], starting_chips=1000, seed=42)
    engine.new_hand()

    # Bob folds, leaving Alice alone
    p = engine.get_current_player()
    if p is not None and p.name != "Alice":
        engine.apply_action(p.name, Action(ActionType.FOLD))
    elif p is not None:
        # Alice acts first in heads-up (dealer = SB), so let her check/call
        actions = engine.get_valid_actions(p.name)
        safe = next(
            (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)),
            actions[0],
        )
        engine.apply_action(p.name, safe)
        # Now Bob folds
        p2 = engine.get_current_player()
        if p2 is not None:
            engine.apply_action(p2.name, Action(ActionType.FOLD))

    tk = PokerToolkit(engine, "Alice")
    result = tk.check_equity(num_simulations=100)
    assert result["win_probability"] == 1.0


# ── place_action("raise", amount=0) ─────────────────────────────────


def test_place_action_raise_zero_uses_minimum(three_player_game):
    """raise with amount=0 should default to minimum raise."""
    engine = three_player_game
    current = engine.get_current_player()
    assert current is not None
    tk = PokerToolkit(engine, current.name)
    result = tk.place_action(action="raise", amount=0)
    assert "error" not in result
    assert result["action"] == "raise"
    assert result["chips_spent"] > 0


# ── place_action("all_in") ──────────────────────────────────────────


def test_place_action_all_in(three_player_game):
    engine = three_player_game
    current = engine.get_current_player()
    assert current is not None
    tk = PokerToolkit(engine, current.name)
    result = tk.place_action(action="all_in")
    assert "error" not in result
    assert result["your_chips"] == 0


# ── view_table when not your turn ────────────────────────────────────


def test_view_table_not_your_turn(three_player_game):
    engine = three_player_game
    current = engine.get_current_player()
    assert current is not None
    other = [p for p in engine.players if p.name != current.name][0]
    tk = PokerToolkit(engine, other.name)
    result = tk.view_table()
    assert result["your_turn"] is False


# ── _get_position for non-special positions ──────────────────────────


def test_get_position_utg(three_player_game):
    """In a 3-player game, one player is BTN, one SB, one BB — none is UTG."""
    engine = three_player_game
    dealer = engine.get_dealer()
    sb, bb = engine.get_sb_bb()
    special = {dealer.name, sb.name, bb.name}
    # In 3-player, all positions are BTN/SB/BB — no one is blank.
    for name in special:
        tk = PokerToolkit(engine, name)
        pos = tk._get_position()
        assert pos in ("BTN", "SB", "BB")


def test_get_position_returns_empty_for_4th_player():
    """In a 4+ player game, UTG+ gets empty string position."""
    engine = PokerEngine(["A", "B", "C", "D"], starting_chips=1000, seed=42)
    engine.new_hand()
    dealer = engine.get_dealer()
    sb, bb = engine.get_sb_bb()
    special = {dealer.name, sb.name, bb.name}
    others = [p.name for p in engine.players if p.name not in special]
    if others:
        tk = PokerToolkit(engine, others[0])
        assert tk._get_position() == ""


# ── view_opponents with shown cards ─────────────────────────────────


def test_view_opponents_shown_cards(three_player_game):
    engine = three_player_game
    # Bob shows cards
    engine.showed_cards["Bob"] = engine.players[1].hole_cards[:2]
    tk = PokerToolkit(engine, "Alice")
    opponents = tk.view_opponents()
    bob_info = next(o for o in opponents if o["name"] == "Bob")
    assert "shown_cards" in bob_info
    assert len(bob_info["shown_cards"]) == 2


# ── place_action when betting is complete ────────────────────────────


def test_place_action_when_round_complete(three_player_game):
    """After betting completes, place_action should return an error."""
    engine = three_player_game
    _call_or_check(engine)
    assert engine.is_betting_round_complete()

    # Now try to act — should fail because no current player
    tk = PokerToolkit(engine, "Alice")
    result = tk.place_action(action="check")
    assert "error" in result
