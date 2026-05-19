"""Tests for the PokerToolkit — tools agents use to interact with the game."""

import pytest

from poker_engine.core.engine import ActionType, PokerEngine
from poker_engine.tools.poker_tools import PokerToolkit


@pytest.fixture
def game():
    engine = PokerEngine(["Alice", "Bob", "Charlie"], starting_chips=1000, seed=42)
    engine.new_hand()
    return engine


def test_view_hand_shows_own_cards(game):
    toolkit = PokerToolkit(game, "Alice")
    result = toolkit.view_hand()
    assert len(result["hole_cards"]) == 2
    assert result["chips"] > 0
    assert isinstance(result["hole_cards"][0], str)


def test_view_hand_includes_evaluation_with_community(game):
    while not game.is_betting_round_complete():
        p = game.get_current_player()
        if p is None:
            break
        actions = game.get_valid_actions(p.name)
        check_call = next(a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL))
        game.apply_action(p.name, check_call)
    game.advance_phase()

    toolkit = PokerToolkit(game, "Alice")
    result = toolkit.view_hand()
    assert "current_hand" in result
    assert "hand_rank" in result


def test_view_table_shows_public_info(game):
    toolkit = PokerToolkit(game, "Alice")
    result = toolkit.view_table()
    assert "pot" in result
    assert "current_bet" in result
    assert "phase" in result
    assert result["phase"] == "PRE_FLOP"
    assert result["players_in_hand"] == 3


def test_check_equity_returns_probabilities(game):
    toolkit = PokerToolkit(game, "Alice")
    result = toolkit.check_equity(num_simulations=100)
    assert "win_probability" in result
    assert "tie_probability" in result
    assert 0.0 <= result["win_probability"] <= 1.0


def test_check_equity_clamps_simulations(game):
    toolkit = PokerToolkit(game, "Alice")
    result = toolkit.check_equity(num_simulations=5)
    assert "win_probability" in result


def test_view_opponents_hides_hole_cards(game):
    toolkit = PokerToolkit(game, "Alice")
    opponents = toolkit.view_opponents()
    assert len(opponents) == 2
    names = [o["name"] for o in opponents]
    assert "Alice" not in names
    assert "Bob" in names
    assert "Charlie" in names
    for opp in opponents:
        assert "hole_cards" not in opp


def test_view_opponents_shows_stats_after_hands(game):
    for p in game.players:
        p.hands_played = 5
        p.total_folds = 2
        p.total_raises = 1
    toolkit = PokerToolkit(game, "Alice")
    opponents = toolkit.view_opponents()
    for opp in opponents:
        assert "stats" in opp
        assert opp["stats"]["fold_rate"] == 0.4


def test_place_action_fold(game):
    current = game.get_current_player()
    toolkit = PokerToolkit(game, current.name)
    result = toolkit.place_action(action="fold")
    assert "error" not in result
    assert result["action"] == "fold"


def test_place_action_call(game):
    current = game.get_current_player()
    toolkit = PokerToolkit(game, current.name)
    result = toolkit.place_action(action="call")
    assert "error" not in result
    assert result["chips_spent"] > 0


def test_place_action_wrong_turn(game):
    current = game.get_current_player()
    other = [p for p in game.players if p.name != current.name][0]
    toolkit = PokerToolkit(game, other.name)
    result = toolkit.place_action(action="fold")
    assert "error" in result


def test_place_action_invalid_action(game):
    current = game.get_current_player()
    toolkit = PokerToolkit(game, current.name)
    result = toolkit.place_action(action="dance")
    assert "error" in result


def test_place_action_raise(game):
    current = game.get_current_player()
    toolkit = PokerToolkit(game, current.name)
    result = toolkit.place_action(action="raise", amount=40)
    assert "error" not in result
    assert result["pot"] > 30


def test_toolkit_get_tools_returns_five(game):
    toolkit = PokerToolkit(game, "Alice")
    tools = toolkit.get_tools()
    assert len(tools) == 5
    names = {t.name for t in tools}
    assert names == {"view_hand", "view_table", "check_equity", "view_opponents", "place_action"}


def test_toolkit_schemas_have_valid_structure(game):
    toolkit = PokerToolkit(game, "Alice")
    schemas = toolkit.registry.get_schemas("anthropic")
    for schema in schemas:
        assert "name" in schema
        assert "description" in schema
        assert "input_schema" in schema


def test_information_hiding_across_toolkits(game):
    tk_alice = PokerToolkit(game, "Alice")
    tk_bob = PokerToolkit(game, "Bob")

    alice_hand = tk_alice.view_hand()
    bob_hand = tk_bob.view_hand()
    assert alice_hand["hole_cards"] != bob_hand["hole_cards"]

    alice_opps = tk_alice.view_opponents()
    assert all(o["name"] != "Alice" for o in alice_opps)
    bob_opps = tk_bob.view_opponents()
    assert all(o["name"] != "Bob" for o in bob_opps)
