"""Main TUI application — wires events to visual components."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.layout import Layout
from rich.live import Live

from poker_engine.tournament.director import TournamentDirector, TournamentResult
from poker_engine.tournament.events import (
    ActionEvent,
    BlindLevelEvent,
    CommentaryEvent,
    EliminationEvent,
    HandEndEvent,
    HandStartEvent,
    PhaseChangeEvent,
    TournamentEvent,
)
from poker_engine.tui.action_feed import ActionFeed
from poker_engine.tui.commentary import CommentaryPanel
from poker_engine.tui.stats_panel import StatsPanel
from poker_engine.tui.table_view import TableView


class PokerTUI:
    """Rich-based terminal UI for watching a poker tournament.

    Subscribes to the director's event bus and renders live updates
    using Rich's Live display with a multi-panel layout.
    """

    def __init__(self, director: TournamentDirector) -> None:
        self._director = director
        self._table_view = TableView()
        self._action_feed = ActionFeed(maxlen=20)
        self._commentary = CommentaryPanel(maxlen=8)
        self._stats = StatsPanel()

        self._current_blind: dict[str, Any] | None = None
        self._hands_played: int = 0
        self._live: Live | None = None

        # Subscribe to events
        self._director.event_bus.subscribe(self._handle_event)

    def _handle_event(self, event: TournamentEvent) -> None:
        """Route a tournament event to the appropriate panel."""
        if isinstance(event, HandStartEvent):
            self._table_view.update_hand_num(event.hand_num)
            self._hands_played = event.hand_num

        elif isinstance(event, PhaseChangeEvent):
            self._table_view.update_community(event.community)

        elif isinstance(event, ActionEvent):
            self._action_feed.add(event.player, event.action, event.amount)
            self._table_view.update_pot(event.pot)
            self._update_player_active(event.player, event.action)

        elif isinstance(event, CommentaryEvent):
            self._commentary.add(event.player, event.text)

        elif isinstance(event, HandEndEvent):
            winners = ", ".join(event.winners)
            self._action_feed.add(
                winners, f"wins ({event.win_reason})"
            )
            # Reset community for next hand
            self._table_view.update_community([])
            self._table_view.update_pot(0)
            self._refresh_standings()

        elif isinstance(event, BlindLevelEvent):
            self._current_blind = {
                "level": event.level,
                "small_blind": event.small_blind,
                "big_blind": event.big_blind,
                "ante": event.ante,
            }
            self._refresh_standings()

        elif isinstance(event, EliminationEvent):
            self._action_feed.add(
                event.player, f"eliminated (#{event.position})"
            )
            self._refresh_standings()

        # Trigger a live refresh if running
        if self._live is not None:
            self._live.update(self.build_layout())

    def _update_player_active(self, player: str, action: str) -> None:
        """Mark a player as active (or folded) in the table view."""
        for p in self._table_view._players:
            p["is_active"] = p["name"] == player
            if p["name"] == player and action == "fold":
                p["folded"] = True

    def _refresh_standings(self) -> None:
        """Pull current standings from the director's tables."""
        standings: list[dict[str, Any]] = []
        for table in self._director._table_manager.tables:
            for p in table.engine.players:
                standings.append({"name": p.name, "chips": p.chips})

        self._stats.update(
            standings,
            blind_level=self._current_blind,
            hands_played=self._hands_played,
        )
        self._table_view.update_players(self._build_table_players())

    def _build_table_players(self) -> list[dict[str, Any]]:
        """Build player info dicts for the table view."""
        players: list[dict[str, Any]] = []
        for table in self._director._table_manager.tables:
            for p in table.engine.players:
                tag = ""
                if hasattr(p, "is_dealer") and p.is_dealer:
                    tag = "BTN"
                players.append({
                    "name": p.name,
                    "chips": p.chips,
                    "position_tag": tag,
                    "is_active": False,
                    "folded": p.folded,
                })
        return players

    def build_layout(self) -> Layout:
        """Construct the Rich Layout for the TUI.

        Layout structure:
            ┌─── Table View (top) ────────────────┐
            ├─── Actions ────┬─── Thoughts ────────┤
            ├─── Stats Panel ─────────────────────┤
            └──────────────────────────────────────┘
        """
        layout = Layout()

        layout.split_column(
            Layout(name="table", size=16),
            Layout(name="middle", size=10),
            Layout(name="stats", minimum_size=6),
        )

        layout["middle"].split_row(
            Layout(name="actions"),
            Layout(name="thoughts"),
        )

        layout["table"].update(self._table_view.render())
        layout["actions"].update(self._action_feed.render())
        layout["thoughts"].update(self._commentary.render())
        layout["stats"].update(self._stats.render())

        return layout

    async def run(self) -> TournamentResult:
        """Run the tournament with live TUI rendering.

        Uses asyncio.gather to run the tournament and TUI refresh
        loop in parallel.

        Returns:
            TournamentResult from the director.
        """
        tournament_task = asyncio.create_task(self._director.run())

        with Live(
            self.build_layout(),
            refresh_per_second=4,
            screen=False,
        ) as live:
            self._live = live
            while not tournament_task.done():
                await asyncio.sleep(0.25)
            live.update(self.build_layout())
            await asyncio.sleep(0.5)
        self._live = None

        return await tournament_task
