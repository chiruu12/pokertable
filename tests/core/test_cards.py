"""Tests for card primitives and hand evaluation."""

from poker_engine.cards import (
    Card,
    HandRank,
    Suit,
    describe_hand,
    evaluate_hand,
    make_deck,
)


def test_deck_has_52_cards():
    assert len(make_deck()) == 52


def test_card_str():
    c = Card(14, Suit.SPADES)
    assert str(c) == "A♠"


def test_pair():
    cards = [
        Card(14, Suit.SPADES),
        Card(14, Suit.HEARTS),
        Card(10, Suit.CLUBS),
        Card(7, Suit.DIAMONDS),
        Card(3, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.PAIR


def test_two_pair():
    cards = [
        Card(14, Suit.SPADES),
        Card(14, Suit.HEARTS),
        Card(10, Suit.CLUBS),
        Card(10, Suit.DIAMONDS),
        Card(3, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.TWO_PAIR


def test_flush():
    cards = [
        Card(14, Suit.HEARTS),
        Card(10, Suit.HEARTS),
        Card(7, Suit.HEARTS),
        Card(4, Suit.HEARTS),
        Card(2, Suit.HEARTS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.FLUSH


def test_straight():
    cards = [
        Card(10, Suit.SPADES),
        Card(9, Suit.HEARTS),
        Card(8, Suit.CLUBS),
        Card(7, Suit.DIAMONDS),
        Card(6, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.STRAIGHT


def test_ace_low_straight():
    cards = [
        Card(14, Suit.SPADES),
        Card(5, Suit.HEARTS),
        Card(4, Suit.CLUBS),
        Card(3, Suit.DIAMONDS),
        Card(2, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.STRAIGHT


def test_full_house():
    cards = [
        Card(13, Suit.SPADES),
        Card(13, Suit.HEARTS),
        Card(13, Suit.CLUBS),
        Card(10, Suit.DIAMONDS),
        Card(10, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.FULL_HOUSE


def test_four_of_a_kind():
    cards = [
        Card(14, Suit.SPADES),
        Card(14, Suit.HEARTS),
        Card(14, Suit.CLUBS),
        Card(14, Suit.DIAMONDS),
        Card(3, Suit.CLUBS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.FOUR_OF_A_KIND


def test_royal_flush():
    cards = [
        Card(14, Suit.SPADES),
        Card(13, Suit.SPADES),
        Card(12, Suit.SPADES),
        Card(11, Suit.SPADES),
        Card(10, Suit.SPADES),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.ROYAL_FLUSH


def test_best_of_7():
    cards = [
        Card(14, Suit.SPADES),
        Card(14, Suit.HEARTS),
        Card(10, Suit.CLUBS),
        Card(7, Suit.DIAMONDS),
        Card(3, Suit.CLUBS),
        Card(14, Suit.CLUBS),
        Card(2, Suit.HEARTS),
    ]
    result = evaluate_hand(cards)
    assert result.rank == HandRank.THREE_OF_A_KIND


def test_hand_comparison():
    flush = evaluate_hand(
        [
            Card(14, Suit.HEARTS),
            Card(10, Suit.HEARTS),
            Card(7, Suit.HEARTS),
            Card(4, Suit.HEARTS),
            Card(2, Suit.HEARTS),
        ]
    )
    pair = evaluate_hand(
        [
            Card(14, Suit.SPADES),
            Card(14, Suit.HEARTS),
            Card(10, Suit.CLUBS),
            Card(7, Suit.DIAMONDS),
            Card(3, Suit.CLUBS),
        ]
    )
    assert flush > pair


def test_describe_hand_pair():
    result = evaluate_hand(
        [
            Card(14, Suit.SPADES),
            Card(14, Suit.HEARTS),
            Card(10, Suit.CLUBS),
            Card(7, Suit.DIAMONDS),
            Card(3, Suit.CLUBS),
        ]
    )
    desc = describe_hand(result)
    assert "Pair" in desc
    assert "A" in desc


def test_describe_hand_full_house():
    result = evaluate_hand(
        [
            Card(13, Suit.SPADES),
            Card(13, Suit.HEARTS),
            Card(13, Suit.CLUBS),
            Card(10, Suit.DIAMONDS),
            Card(10, Suit.CLUBS),
        ]
    )
    desc = describe_hand(result)
    assert "Full House" in desc
