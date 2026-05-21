"""Tests for terminal rendering components."""

from poker_engine.tui.action_feed import ActionFeed
from poker_engine.tui.chat_panel import ChatPanel
from poker_engine.tui.commentary import CommentaryPanel
from poker_engine.tui.stats_panel import StatsPanel
from poker_engine.tui.table_view import TableView


def test_table_view_accepts_compact_height() -> None:
    view = TableView()
    view.update_hand_num(3)
    view.update_pot(1200)
    view.update_community(["A♠", "K♦", "7♥"])
    view.update_players(
        [
            {"name": "LFM-2.5", "chips": 500, "hole_cards": ["A♣", "Q♣"]},
            {"name": "GPT-OSS", "chips": 450, "hole_cards": ["9♠", "9♥"]},
            {"name": "Kimi", "chips": 550, "hole_cards": ["2♦", "3♦"]},
        ]
    )

    panel = view.render(height=12)

    assert panel.height == 12


def test_action_feed_uses_allocated_height() -> None:
    feed = ActionFeed(maxlen=20)
    for idx in range(10):
        feed.add(f"Very Long Agent Name {idx}", "raise", amount=idx * 10)

    panel = feed.render(height=5)

    assert panel.height == 5


def test_chat_panel_truncates_and_uses_allocated_height() -> None:
    chat = ChatPanel(maxlen=20)
    long_msg = "word " * 80
    chat.add("Verbose Agent", long_msg)

    panel = chat.render(height=6)

    assert panel.height == 6
    rendered = str(panel.renderable)
    assert "..." in rendered
    assert long_msg not in rendered


def test_commentary_panel_truncates_and_uses_allocated_height() -> None:
    thoughts = CommentaryPanel(maxlen=20)
    long_text = "I am thinking about ranges, blockers, pressure, and table image. " * 4
    thoughts.add("Kimi", long_text)

    panel = thoughts.render(height=6)

    assert panel.height == 6
    rendered = str(panel.renderable)
    assert "..." in rendered
    assert long_text not in rendered


def test_stats_panel_uses_allocated_height() -> None:
    stats = StatsPanel()
    stats.update(
        [
            {"name": "LFM-2.5", "chips": 500},
            {"name": "GPT-OSS", "chips": 450},
            {"name": "Kimi", "chips": 550},
        ],
        blind_level={"level": 1, "small_blind": 5, "big_blind": 10, "ante": 0},
        hands_played=4,
    )

    panel = stats.render(height=7)

    assert panel.height == 7
