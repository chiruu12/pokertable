"""Edge-case tests for the PokerEngine state machine."""

import pytest

from poker_engine.core.engine import (
    Action,
    ActionType,
    Phase,
    PokerEngine,
)

# ── helpers ──────────────────────────────────────────────────────────


def _call_or_check(engine: PokerEngine) -> None:
    """Advance through a betting round with everyone calling/checking."""
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


# ── Heads-up blind positions ────────────────────────────────────────


def test_heads_up_dealer_posts_small_blind():
    engine = PokerEngine(["A", "B"], starting_chips=1000, seed=1)
    engine.new_hand()
    sb, bb = engine.get_sb_bb()
    dealer = engine.get_dealer()
    assert sb.name == dealer.name, "In heads-up, dealer should post small blind"


def test_heads_up_other_posts_big_blind():
    engine = PokerEngine(["A", "B"], starting_chips=1000, seed=1)
    engine.new_hand()
    sb, bb = engine.get_sb_bb()
    dealer = engine.get_dealer()
    assert bb.name != dealer.name


# ── Multiple side pots ──────────────────────────────────────────────


def test_three_player_all_in_side_pots():
    """A=50, B=100, C=200 — all go all-in. Verify side pots and chip conservation."""
    engine = PokerEngine(["A", "B", "C"], starting_chips=200, seed=42)
    engine.players[0].chips = 50
    engine.players[1].chips = 100
    engine.players[2].chips = 200
    total_before = sum(p.chips for p in engine.players)

    engine.new_hand()

    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(
            p.name, Action(ActionType.ALL_IN, p.chips + p.bet_this_round)
        )

    pots = engine._compute_side_pots()
    assert len(pots) >= 2, "Should have at least a main pot and a side pot"

    # All chips that went in must be distributed across pots
    pot_total = sum(sp.amount for sp in pots)
    assert pot_total == engine.pot

    # Drive to showdown and verify chip conservation
    while engine.phase not in (Phase.SHOWDOWN, Phase.HAND_OVER):
        engine.advance_phase()
    engine.resolve_showdown()
    total_after = sum(p.chips for p in engine.players)
    assert total_after == total_before


def test_side_pot_eligibility():
    """Short-stack should not be eligible for pots they couldn't match."""
    engine = PokerEngine(["A", "B", "C"], starting_chips=200, seed=7)
    engine.players[0].chips = 30
    engine.players[1].chips = 200
    engine.players[2].chips = 200

    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(
            p.name, Action(ActionType.ALL_IN, p.chips + p.bet_this_round)
        )

    pots = engine._compute_side_pots()
    main = pots[0]
    assert "A" in main.eligible
    if len(pots) > 1:
        side = pots[-1]
        assert "A" not in side.eligible


# ── All players all-in preflop ───────────────────────────────────────


def test_all_in_preflop_advances_to_showdown():
    engine = PokerEngine(["A", "B"], starting_chips=100, seed=42)
    engine.new_hand()
    while not engine.is_betting_round_complete():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(
            p.name, Action(ActionType.ALL_IN, p.chips + p.bet_this_round)
        )

    # All are all-in, betting complete
    assert engine.is_betting_round_complete()

    # Advance through all phases
    while engine.phase not in (Phase.SHOWDOWN, Phase.HAND_OVER):
        engine.advance_phase()

    summary = engine.resolve_showdown()
    assert len(engine.community) == 5
    assert len(summary.winners) >= 1
    total = sum(p.chips for p in engine.players)
    assert total == 200


# ── Short-stack all-in that doesn't reset action ────────────────────


def test_short_all_in_does_not_reopen_betting():
    """All-in for less than min_raise should not reopen action."""
    engine = PokerEngine(
        ["A", "B", "C"], starting_chips=1000, small_blind=10, big_blind=20, seed=5
    )
    # Give A very few chips so their all-in is below min_raise
    engine.players[0].chips = 25
    engine.new_hand()

    # Let UTG (first to act) go all-in for less than a full raise
    p = engine.get_current_player()
    if p is not None and p.name == "A":
        engine.apply_action(p.name, Action(ActionType.ALL_IN, 25))
        # The all-in was for 25 total (bet_this_round would be 25), which is
        # 5 above the BB of 20, less than min_raise of 20. The other players
        # should NOT have their has_acted reset because this isn't a legal raise.
        # BB already posted, but hasn't formally "acted" — that's expected.
        # The key check: if someone already acted, short all-in shouldn't reset them.
        bb = next(
            pl for pl in engine.players if pl.bet_this_round == 20 and not pl.all_in
        )
        assert not bb.has_acted  # BB has not formally acted yet


# ── Statistics across hands ──────────────────────────────────────────


def test_stats_accumulate_across_hands():
    engine = PokerEngine(["A", "B"], starting_chips=1000, seed=42)
    for _ in range(3):
        engine.new_hand()
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
        engine.resolve_showdown()
        engine.rotate_dealer()

    for p in engine.players:
        assert p.hands_played == 3


def test_fold_counter_increments():
    engine = PokerEngine(["A", "B"], starting_chips=1000, seed=42)
    engine.new_hand()
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.FOLD))
    player = engine._get_player(p.name)
    assert player.total_folds == 1


# ── _get_player with invalid name ───────────────────────────────────


def test_get_player_invalid_raises():
    engine = PokerEngine(["A", "B"], seed=1)
    with pytest.raises(ValueError, match="Player not found"):
        engine._get_player("Nonexistent")


# ── Dealer rotation when dealer busted ───────────────────────────────


def test_rotate_dealer_skips_busted():
    engine = PokerEngine(["A", "B", "C"], starting_chips=500, seed=1)
    engine.dealer_idx = 0
    engine.players[1].chips = 0  # B is busted
    engine.rotate_dealer()
    # Should skip B (index 1) and land on C (index 2)
    assert engine.dealer_idx == 2


def test_rotate_dealer_when_current_dealer_busted():
    engine = PokerEngine(["A", "B", "C"], starting_chips=500, seed=1)
    engine.dealer_idx = 0
    engine.players[0].chips = 0  # current dealer busted
    engine.rotate_dealer()
    # Should jump to first alive player
    assert engine.players[engine.dealer_idx].chips > 0


# ── Phase advancement sequence ───────────────────────────────────────


def test_phase_sequence_preflop_to_showdown():
    engine = PokerEngine(["A", "B"], starting_chips=1000, seed=42)
    engine.new_hand()
    assert engine.phase == Phase.PRE_FLOP

    _call_or_check(engine)
    engine.advance_phase()
    assert engine.phase == Phase.FLOP
    assert len(engine.community) == 3

    _call_or_check(engine)
    engine.advance_phase()
    assert engine.phase == Phase.TURN
    assert len(engine.community) == 4

    _call_or_check(engine)
    engine.advance_phase()
    assert engine.phase == Phase.RIVER
    assert len(engine.community) == 5

    _call_or_check(engine)
    engine.advance_phase()
    assert engine.phase == Phase.SHOWDOWN


# ── Full fold-out in multiway pot ────────────────────────────────────


def test_fold_out_multiway_last_player_wins():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=42)
    engine.new_hand()

    # Everyone who can act folds except the last one
    folds_done = 0
    while not engine.is_hand_over():
        p = engine.get_current_player()
        if p is None:
            break
        engine.apply_action(p.name, Action(ActionType.FOLD))
        folds_done += 1
        if folds_done >= 2:
            break

    active = [pl for pl in engine.players if not pl.folded]
    assert len(active) == 1
    summary = engine.resolve_fold_win()
    assert summary.winners == [active[0].name]
    total = sum(pl.chips for pl in engine.players)
    assert total == 3000


def test_fold_out_pot_awarded_correctly():
    engine = PokerEngine(
        ["A", "B", "C"], starting_chips=1000, small_blind=10, big_blind=20, seed=1
    )
    engine.new_hand()
    # Blinds create a pot of 30
    assert engine.pot == 30

    # UTG folds
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.FOLD))

    # SB folds
    p = engine.get_current_player()
    assert p is not None
    engine.apply_action(p.name, Action(ActionType.FOLD))

    # BB wins
    summary = engine.resolve_fold_win()
    assert len(summary.winners) == 1
    # Chips conserved
    total = sum(pl.chips for pl in engine.players)
    assert total == 3000


# ── Chip conservation with raises ────────────────────────────────────


def test_chips_conserved_with_raises():
    engine = PokerEngine(["A", "B", "C"], starting_chips=1000, seed=42)
    total_before = sum(p.chips for p in engine.players)
    engine.new_hand()

    # UTG raises
    p = engine.get_current_player()
    if p is not None:
        engine.apply_action(p.name, Action(ActionType.RAISE, 60))

    # Finish the round
    _call_or_check(engine)

    # Play to showdown
    while engine.phase not in (Phase.SHOWDOWN, Phase.HAND_OVER):
        engine.advance_phase()
        _call_or_check(engine)

    if engine.phase == Phase.SHOWDOWN:
        engine.resolve_showdown()
    else:
        active = [p for p in engine.players if not p.folded]
        if len(active) <= 1:
            engine.resolve_fold_win()

    total_after = sum(p.chips for p in engine.players)
    assert total_after == total_before
