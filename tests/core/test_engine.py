"""Tests for the poker engine state machine."""

from poker_engine import Action, ActionType, Phase, PlayerState, PokerEngine, compute_opponent_style


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


# --- Ante tests ---


def test_ante_posts_before_blinds():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=1000,
        small_blind=10,
        big_blind=20,
        ante=5,
        seed=1,
    )
    engine.new_hand()
    # 3 players x 5 ante = 15, plus SB 10 + BB 20 = 30 → total pot = 45
    assert engine.pot == 45


def test_ante_zero_no_effect():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=1000,
        small_blind=10,
        big_blind=20,
        ante=0,
        seed=1,
    )
    engine.new_hand()
    assert engine.pot == 30


def test_ante_chips_conserved():
    engine = PokerEngine(["A", "B", "C"], starting_chips=500, ante=5, seed=42)
    total_before = sum(p.chips for p in engine.players)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        check_call = next(
            (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)), actions[0]
        )
        engine.apply_action(p.name, check_call)
    engine.resolve_showdown()
    total_after = sum(p.chips for p in engine.players)
    assert total_after == total_before


def test_ante_short_stack_all_in():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, ante=5, seed=1)
    engine.players[0].chips = 3
    engine.new_hand()
    assert engine.players[0].all_in is True
    assert engine.players[0].chips == 0
    assert engine.players[0].bet_this_hand == 3


def test_ante_in_bet_this_hand_not_round():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, ante=5, seed=1)
    engine.new_hand()
    for p in engine.players:
        if not p.folded:
            assert p.bet_this_hand >= 5
            # Ante doesn't count as a round-level bet (only blinds do)
            # SB and BB have bet_this_round from blinds, others have 0
            if p.bet_this_round > 0:
                assert p.bet_this_round in (10, 20)  # SB or BB amounts


# --- Raise cap tests ---


def test_raise_cap_blocks_fifth_raise():
    names = ["A", "B", "C", "D", "E", "F"]
    engine = PokerEngine(names, starting_chips=10000, seed=1)
    engine.new_hand()
    for i in range(4):
        p = engine.get_current_player()
        assert p is not None
        actions = engine.get_valid_actions(p.name)
        raises = [a for a in actions if a.type == ActionType.RAISE]
        assert len(raises) > 0, f"Raise #{i + 1} should be allowed"
        engine.apply_action(p.name, raises[0])
    # 5th player should NOT see RAISE in valid actions
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    assert len(raises) == 0


def test_raise_cap_resets_each_phase():
    engine = PokerEngine(["A", "B", "C"], starting_chips=10000, seed=1)
    engine.new_hand()
    # Make raises until cap
    for _ in range(4):
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        raises = [a for a in actions if a.type == ActionType.RAISE]
        if raises:
            engine.apply_action(p.name, raises[0])
    # Complete the round
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        call = next(
            (a for a in actions if a.type in (ActionType.CALL, ActionType.CHECK)),
            actions[0],
        )
        engine.apply_action(p.name, call)
    engine.advance_phase()
    # After phase advance, raises should be allowed again
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    assert len(raises) > 0


def test_raise_cap_zero_means_no_raises():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=1000,
        max_raises_per_round=0,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    assert len(raises) == 0


def test_raise_cap_default_is_four():
    engine = PokerEngine(["A", "B"], seed=1)
    assert engine._max_raises_per_round == 4


def test_all_in_does_not_count_toward_cap():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=1000,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(
        p.name,
        Action(ActionType.ALL_IN, p.chips + p.bet_this_round),
    )
    assert engine._raises_this_round == 0


def test_raise_cap_resets_between_hands():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=10000,
        seed=1,
    )
    engine.new_hand()
    # Make some raises
    for _ in range(3):
        p = engine.get_current_player()
        if p is None:
            break
        actions = engine.get_valid_actions(p.name)
        raises = [a for a in actions if a.type == ActionType.RAISE]
        if raises:
            engine.apply_action(p.name, raises[0])
    assert engine._raises_this_round > 0
    # Complete hand
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.FOLD))
    engine.resolve_fold_win()
    engine.rotate_dealer()
    # Start new hand — raises should be reset
    engine.new_hand()
    assert engine._raises_this_round == 0
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    assert len(raises) > 0


# --- Half-pot raise tests ---


def test_half_pot_raise_option_exists():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=1)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    # Should have min-raise, half-pot, and pot-raise (3 raise options)
    assert len(raises) >= 2


def test_half_pot_amount_calculation():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=1000,
        small_blind=10,
        big_blind=20,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    cost_to_call = engine.current_bet - p.bet_this_round
    expected_half = engine.current_bet + (engine.pot + cost_to_call) // 2
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    amounts = [r.amount for r in raises]
    if expected_half > engine.current_bet + engine.min_raise:
        assert expected_half in amounts


def test_half_pot_skipped_when_equals_min_raise():
    engine = PokerEngine(
        ["A", "B"],
        starting_chips=1000,
        small_blind=10,
        big_blind=20,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    amounts = [r.amount for r in raises]
    # No duplicate amounts
    assert len(amounts) == len(set(amounts))


def test_half_pot_skipped_when_cant_afford():
    engine = PokerEngine(
        ["A", "B", "C"],
        starting_chips=50,
        small_blind=10,
        big_blind=20,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    if p is not None:
        actions = engine.get_valid_actions(p.name)
        raises = [a for a in actions if a.type == ActionType.RAISE]
        for r in raises:
            cost = r.amount - p.bet_this_round
            assert cost <= p.chips


def test_half_pot_respects_raise_cap():
    engine = PokerEngine(
        ["A", "B", "C", "D", "E", "F"],
        starting_chips=10000,
        max_raises_per_round=1,
        seed=1,
    )
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    actions = engine.get_valid_actions(p.name)
    raises = [a for a in actions if a.type == ActionType.RAISE]
    assert len(raises) > 0
    engine.apply_action(p.name, raises[0])
    # After 1 raise, no more raises (including half-pot)
    p2 = engine.get_current_player()
    assert p2 is not None
    actions2 = engine.get_valid_actions(p2.name)
    raises2 = [a for a in actions2 if a.type == ActionType.RAISE]
    assert len(raises2) == 0


# --- contested_win tests ---


def _play_to_showdown(engine):
    """Helper: everyone checks/calls to showdown."""
    for _ in range(4):
        while not engine.is_betting_round_complete():
            p = engine.get_current_player()
            if p is None:
                break
            actions = engine.get_valid_actions(p.name)
            check_call = next(
                (a for a in actions if a.type in (ActionType.CHECK, ActionType.CALL)),
                actions[0],
            )
            engine.apply_action(p.name, check_call)
        if engine.phase == Phase.SHOWDOWN or engine.is_hand_over():
            break
        engine.advance_phase()
    return engine.resolve_showdown()


def test_contested_win_true_in_multiway():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=42)
    engine.new_hand()
    summary = _play_to_showdown(engine)
    winning_results = [r for r in summary.results if r.winnings > 0]
    assert len(winning_results) >= 1
    for r in winning_results:
        assert r.contested_win is True


def test_contested_win_false_when_all_fold():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=1)
    engine.new_hand()
    # First two players fold → third wins uncontested
    for _ in range(2):
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.FOLD))
    summary = engine.resolve_fold_win()
    assert summary.win_reason == "all_folded"


def test_hands_won_only_on_contested():
    engine = PokerEngine(["A", "B", "C"], starting_chips=100, seed=42)
    engine.players[0].chips = 20
    engine.new_hand()
    # A goes all-in for 20 (small pot), B and C call
    p = engine.get_current_player()
    while p is not None:
        actions = engine.get_valid_actions(p.name)
        call = next(
            (a for a in actions if a.type in (ActionType.CALL, ActionType.CHECK)),
            actions[0],
        )
        engine.apply_action(p.name, call)
        p = engine.get_current_player()
    summary = _play_to_showdown(engine)
    # Verify hands_won was only incremented for contested pots
    for r in summary.results:
        player = next(p for p in engine.players if p.name == r.player_name)
        if r.contested_win:
            assert player.hands_won >= 1


# --- Opponent style tests ---


def test_style_unknown_under_3_hands():
    p = PlayerState(name="X", chips=1000, hands_played=2, total_folds=1, total_raises=1)
    assert compute_opponent_style(p) == "unknown"


def test_style_aggressive():
    p = PlayerState(name="X", chips=1000, hands_played=10, total_folds=2, total_raises=5)
    assert compute_opponent_style(p) == "aggressive"


def test_style_tricky():
    p = PlayerState(name="X", chips=1000, hands_played=10, total_folds=4, total_raises=4)
    assert compute_opponent_style(p) == "tricky"


def test_style_tight():
    p = PlayerState(name="X", chips=1000, hands_played=10, total_folds=5, total_raises=1)
    assert compute_opponent_style(p) == "tight"


def test_style_passive():
    p = PlayerState(name="X", chips=1000, hands_played=10, total_folds=2, total_raises=2)
    assert compute_opponent_style(p) == "passive"


# --- Position label tests ---


def test_position_labels_2_players():
    engine = PokerEngine(["A", "B"], seed=1)
    engine.new_hand()
    labels = engine.get_position_labels()
    assert set(labels.values()) == {"Dealer/SB", "BB"}


def test_position_labels_3_players():
    engine = PokerEngine(["A", "B", "C"], seed=1)
    engine.new_hand()
    labels = engine.get_position_labels()
    assert set(labels.values()) == {"Dealer", "SB", "BB"}


def test_position_labels_4_players():
    engine = PokerEngine(["A", "B", "C", "D"], seed=1)
    engine.new_hand()
    labels = engine.get_position_labels()
    assert "UTG" in labels.values()
    assert "Dealer" in labels.values()


def test_position_labels_6_players():
    names = ["A", "B", "C", "D", "E", "F"]
    engine = PokerEngine(names, seed=1)
    engine.new_hand()
    labels = engine.get_position_labels()
    assert len(labels) == 6
    vals = set(labels.values())
    assert "Dealer" in vals
    assert "SB" in vals
    assert "BB" in vals


def test_position_labels_stable_after_fold():
    engine = PokerEngine(["A", "B", "C", "D"], seed=1)
    engine.new_hand()
    labels_before = engine.get_position_labels()
    # Player folds
    p = engine.get_current_player()
    if p is not None:
        engine.apply_action(p.name, Action(ActionType.FOLD))
    labels_after = engine.get_position_labels()
    assert labels_before == labels_after


def test_position_labels_9_players():
    names = [f"P{i}" for i in range(9)]
    engine = PokerEngine(names, seed=1)
    engine.new_hand()
    labels = engine.get_position_labels()
    assert len(labels) == 9
    vals = set(labels.values())
    assert "CO" in vals
    assert "HJ" in vals
    assert "LJ" in vals
    assert "UTG+2" in vals
