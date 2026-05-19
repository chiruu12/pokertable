"""Main TUI application — wires events to visual components."""

from __future__ import annotations

import asyncio
from typing import Any

from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from poker_engine.tournament.director import TournamentDirector, TournamentResult
from poker_engine.tournament.events import (
    ActionEvent,
    BlindLevelEvent,
    CardsDealtEvent,
    CommentaryEvent,
    EliminationEvent,
    HandEndEvent,
    HandStartEvent,
    PhaseChangeEvent,
    ShowdownEvent,
    TableTalkEvent,
    TournamentEvent,
)
from poker_engine.tui.action_feed import ActionFeed
from poker_engine.tui.card_display import style_for_card
from poker_engine.tui.chat_panel import ChatPanel
from poker_engine.tui.commentary import CommentaryPanel
from poker_engine.tui.stats_panel import StatsPanel
from poker_engine.tui.table_view import TableView


class PokerTUI:
    """Rich-based terminal UI for watching a poker tournament.

    All state is driven purely by events — the TUI never reads from the
    engine directly. This keeps the board and action feed perfectly in sync.
    """

    def __init__(self, director: TournamentDirector) -> None:
        self._director = director
        self._table_view = TableView()
        self._action_feed = ActionFeed(maxlen=20)
        self._chat = ChatPanel(maxlen=12)
        self._commentary = CommentaryPanel(maxlen=8)
        self._stats = StatsPanel()

        self._current_blind: dict[str, Any] | None = None
        self._hands_played: int = 0
        self._live: Live | None = None

        self._player_state: dict[str, dict[str, Any]] = {}

        self._director.event_bus.subscribe(self._handle_event)

    def _handle_event(self, event: TournamentEvent) -> None:
        if isinstance(event, HandStartEvent):
            self._hands_played = event.hand_num
            self._table_view.update_hand_num(event.hand_num)
            self._table_view.update_community([])
            self._table_view.update_pot(0)
            self._action_feed.add("Dealer", f"Hand #{event.hand_num}")
            self._sync_chips_from_engine()
            for ps in self._player_state.values():
                ps["folded"] = False
                ps["is_active"] = False
                ps["hole_cards"] = []

        elif isinstance(event, CardsDealtEvent):
            for name, cards in event.hands.items():
                if name in self._player_state:
                    self._player_state[name]["hole_cards"] = cards

        elif isinstance(event, PhaseChangeEvent):
            self._table_view.update_community(event.community)
            line = Text()
            line.append("Board ", style="bold yellow")
            line.append(f"{event.phase}: ", style="yellow")
            for i, c in enumerate(event.community):
                if i > 0:
                    line.append(" ")
                line.append(c, style=style_for_card(c))
            self._action_feed.add_rich(line)

        elif isinstance(event, ActionEvent):
            self._action_feed.add(event.player, event.action, event.amount)
            self._table_view.update_pot(event.pot)
            for ps in self._player_state.values():
                ps["is_active"] = False
            if event.player in self._player_state:
                self._player_state[event.player]["is_active"] = True
                if event.action == "fold":
                    self._player_state[event.player]["folded"] = True
            self._sync_chips_from_engine()

        elif isinstance(event, CommentaryEvent):
            self._commentary.add(event.player, event.text)

        elif isinstance(event, TableTalkEvent):
            self._chat.add(event.player, event.message)

        elif isinstance(event, ShowdownEvent):
            for r in event.results:
                cards = " ".join(r.get("cards", []))
                hand = r.get("hand", "")
                won = r.get("winnings", 0)
                marker = "★" if won > 0 else " "
                self._action_feed.add(f"{marker} {r['player']}", f"{cards} → {hand}")

        elif isinstance(event, HandEndEvent):
            winners = ", ".join(event.winners)
            self._action_feed.add(winners, f"wins ({event.win_reason})")
            self._sync_chips_from_engine()

        elif isinstance(event, BlindLevelEvent):
            self._current_blind = {
                "level": event.level,
                "small_blind": event.small_blind,
                "big_blind": event.big_blind,
                "ante": event.ante,
            }

        elif isinstance(event, EliminationEvent):
            self._action_feed.add(event.player, f"eliminated (#{event.position})")

        self._push_state_to_views()

        if self._live is not None:
            self._live.update(self.build_layout())

    def _sync_chips_from_engine(self) -> None:
        """Pull chip counts and position tags from engine (these change on actions)."""
        for table in self._director.tables:
            engine = table.engine
            dealer = engine.get_dealer()
            try:
                sb, bb = engine.get_sb_bb()
                sb_name, bb_name = sb.name, bb.name
            except (IndexError, ValueError):
                sb_name = bb_name = ""

            for p in engine.players:
                if p.name not in self._player_state:
                    self._player_state[p.name] = {
                        "name": p.name,
                        "chips": p.chips,
                        "position_tag": "",
                        "is_active": False,
                        "folded": False,
                        "hole_cards": [],
                    }
                ps = self._player_state[p.name]
                ps["chips"] = p.chips

                tag = ""
                if p.name == dealer.name:
                    tag = "BTN"
                elif p.name == sb_name:
                    tag = "SB"
                elif p.name == bb_name:
                    tag = "BB"
                ps["position_tag"] = tag

    def _push_state_to_views(self) -> None:
        """Push current player state to table view and stats panel."""
        player_list = list(self._player_state.values())
        self._table_view.update_players(player_list)

        standings = [{"name": ps["name"], "chips": ps["chips"]} for ps in player_list]
        self._stats.update(
            standings,
            blind_level=self._current_blind,
            hands_played=self._hands_played,
        )

    def build_layout(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="table", size=18),
            Layout(name="middle", size=10),
            Layout(name="stats", size=10),
        )
        layout["middle"].split_row(
            Layout(name="actions", ratio=2),
            Layout(name="chat", ratio=2),
            Layout(name="thoughts", ratio=2),
        )
        layout["table"].update(self._table_view.render())
        layout["actions"].update(self._action_feed.render())
        layout["chat"].update(self._chat.render())
        layout["thoughts"].update(self._commentary.render())
        layout["stats"].update(self._stats.render())
        return layout

    async def run(self) -> TournamentResult:
        self._sync_chips_from_engine()
        self._push_state_to_views()

        tournament_task = asyncio.create_task(self._director.run())

        with Live(
            self.build_layout(),
            refresh_per_second=10,
            screen=False,
        ) as live:
            self._live = live
            while not tournament_task.done():
                await asyncio.sleep(0.1)
            live.update(self.build_layout())
            await asyncio.sleep(0.5)
        self._live = None

        return await tournament_task
