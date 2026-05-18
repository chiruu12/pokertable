"""Tests for the poker engine state machine."""

from poker_engine import Action, ActionType, Phase, PokerEngine


def test_new_hand_deals_cards():
    engine = PokerEngine(["A", "B", "C"], seed=1)
    engine.new_hand()
    for p in engine.players:
        assert len(p.hole_cards) == 2
    assert engine.phase == Phase.PRE_FLOP


def test_blinds_posted():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, small_blind=10, big_blind=20, seed=1)
    engine.new_hand()
    assert engine.pot == 30
    assert engine.current_bet == 20


def test_betting_round_completes_on_all_call():
    engine = PokerEngine(["A", "B", "C"], seed=1)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        call_or_check = next(
            (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)), actions[0]
        )
        engine.apply_action(p.name, call_or_check)
    assert engine.is_betting_round_complete()


def test_raise_resets_action():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=1)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.RAISE, 40))
    assert not engine.is_betting_round_complete()


def test_advance_to_flop():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.CALL, engine.current_bet))
    engine.advance_phase()
    assert engine.phase == Phase.FLOP
    assert len(engine.community) == 3


def test_full_hand_to_showdown():
    engine = PokerEngine(["A", "B"], seed=42)
    engine.new_hand()
    for phase in [Phase.PRE_FLOP, Phase.FLOP, Phase.TURN, Phase.RIVER]:
        while not engine.is_betting_round_complete():
            p = engine.get_current_player()
            if p is None:
                break
            actions = engine.get_valid_actions(p.name)
            check_call = next(
                (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)), actions[0]
            )
            engine.apply_action(p.name, check_call)
        if engine.phase == Phase.RIVER:
            break
        engine.advance_phase()
    summary = engine.resolve_showdown()
    assert len(summary.winners) >= 1
    assert summary.win_reason == "showdown"
    total = sum(p.chips for p in engine.players)
    assert total == 2000


def test_fold_wins_pot():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.FOLD))
    assert engine.is_hand_over()
    summary = engine.resolve_fold_win()
    assert summary.win_reason == "all_folded"
    total = sum(p.chips for p in engine.players)
    assert total == 2000


def test_all_in_side_pot():
    engine = PokerEngine(["A", "B", "C"], starting_chips=100, seed=42)
    engine.players[0].chips = 50
    total_before = sum(p.chips for p in engine.players)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.ALL_IN, p.chips + p.bet_this_round))
    while engine.phase not in (Phase.SHOWDOWN, Phase.HAND_OVER):
        engine.advance_phase()
    engine.resolve_showdown()
    total_after = sum(p.chips for p in engine.players)
    assert total_after == total_before


def test_dealer_rotates():
    engine = PokerEngine(["A", "B", "C"], seed=1)
    d1 = engine.dealer_idx
    engine.rotate_dealer()
    d2 = engine.dealer_idx
    assert d1 != d2


def test_tournament_over_when_one_left():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.players[0].chips = 0
    assert engine.is_tournament_over()


def test_show_cards_records():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.SHOW_CARDS))
    assert p.name in engine.showed_cards
    assert len(engine.showed_cards[p.name]) == 2


def test_valid_actions_include_fold_and_call():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    types = [a.type for a in actions]
    assert ActionType.FOLD in types
    assert ActionType.CALL in types or ActionType.CHECK in types


def test_chips_conserved_across_hand():
    engine = PokerEngine(["A", "B", "C"], starting_chips=500, seed=99)
    total_before = sum(p.chips for p in engine.players)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        engine.apply_action(p.name, actions[1])
    engine.advance_phase()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.CHECK))
    engine.resolve_showdown()
    total_after = sum(p.chips for p in engine.players)
    assert total_after == total_before
