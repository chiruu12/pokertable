"""Poker Engine — Pure Texas Hold'em for AI agents."""

import sys

__version__ = "1.0.0"

from poker_engine.core import (
    cards,  # noqa: F401
    engine,  # noqa: F401
    equity,  # noqa: F401
)
from poker_engine.core.cards import (
    Card,
    HandRank,
    HandResult,
    Suit,
    describe_hand,
    evaluate_hand,
    make_deck,
)
from poker_engine.core.engine import (
    Action,
    ActionResult,
    ActionType,
    HandSummary,
    Phase,
    PlayerState,
    PokerEngine,
    ShowdownResult,
    SidePot,
)
from poker_engine.core.equity import EquityResult, calculate_equity

sys.modules["poker_engine.cards"] = cards
sys.modules["poker_engine.engine"] = engine
# Note: poker_engine.equity is now a real package (not an alias for core.equity)

__all__ = [
    "Action",
    "ActionResult",
    "ActionType",
    "Card",
    "EquityResult",
    "HandRank",
    "HandResult",
    "HandSummary",
    "Phase",
    "PlayerState",
    "PokerEngine",
    "ShowdownResult",
    "SidePot",
    "Suit",
    "calculate_equity",
    "describe_hand",
    "evaluate_hand",
    "make_deck",
]
