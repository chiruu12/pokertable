"""Tests for the equity calculator."""

from poker_engine.cards import Card, Suit

from poker_engine.equity import calculate_equity


def test_pocket_aces_high_equity():
    hole = [Card(14, Suit.SPADES), Card(14, Suit.HEARTS)]
    eq = calculate_equity(hole, [], num_opponents=1, seed=42)
    assert eq.win_probability > 0.7


def test_equity_with_community():
    hole = [Card(14, Suit.SPADES), Card(13, Suit.SPADES)]
    community = [Card(12, Suit.SPADES), Card(7, Suit.HEARTS), Card(2, Suit.CLUBS)]
    eq = calculate_equity(hole, community, num_opponents=1, seed=42)
    assert eq.win_probability > 0.5
    assert len(eq.hand_improvement) > 0


def test_equity_returns_current_hand():
    hole = [Card(14, Suit.SPADES), Card(14, Suit.HEARTS)]
    community = [Card(14, Suit.CLUBS), Card(7, Suit.DIAMONDS), Card(3, Suit.HEARTS)]
    eq = calculate_equity(hole, community, num_opponents=1, seed=42)
    assert "Three" in eq.current_hand


def test_equity_no_opponents():
    hole = [Card(2, Suit.CLUBS), Card(3, Suit.DIAMONDS)]
    eq = calculate_equity(hole, [], num_opponents=0, seed=42)
    assert eq.win_probability == 1.0


def test_equity_reproducible():
    hole = [Card(10, Suit.HEARTS), Card(10, Suit.DIAMONDS)]
    eq1 = calculate_equity(hole, [], num_opponents=2, seed=42)
    eq2 = calculate_equity(hole, [], num_opponents=2, seed=42)
    assert eq1.win_probability == eq2.win_probability
