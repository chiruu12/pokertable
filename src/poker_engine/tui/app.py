"""Main TUI application — wires events to visual components.

Board reveals (PhaseChangeEvent) are queued and only flushed to the
display right before the next ActionEvent, ShowdownEvent, or HandEndEvent.
This keeps the table and action feed visually in sync even when LLM
decisions take seconds.
"""

from __future__ import annotations

import asyncio
from typing import Any

from rich.console import Console
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
    """Rich-based terminal UI for watching a poker tournament."""

    def __init__(self, director: TournamentDirector) -> None:
        self._director = director
        self._table_view = TableView()
        self._action_feed = ActionFeed(maxlen=20)
        self._chat = ChatPanel(maxlen=12)
        self._commentary = CommentaryPanel(maxlen=8)
        self._stats = StatsPanel()

        self._current_blind: dict[str, Any] | None = None
        self._hands_played: int = 0
        self._console = Console()
        self._live: Live | None = None
        self._dirty = False

        self._player_state: dict[str, dict[str, Any]] = {}
        self._queued_phases: list[PhaseChangeEvent] = []

        self._director.event_bus.subscribe(self._handle_event)

    def _flush_queued_phases(self) -> None:
        """Render any queued board reveals into table view + action feed."""
        for phase_evt in self._queued_phases:
            self._table_view.update_community(phase_evt.community)
            line = Text()
            line.append("Board ", style="bold yellow")
            line.append(f"{phase_evt.phase}: ", style="yellow")
            for i, c in enumerate(phase_evt.community):
                if i > 0:
                    line.append(" ")
                line.append(c, style=style_for_card(c))
            self._action_feed.add_rich(line)
        self._queued_phases.clear()

    def _handle_event(self, event: TournamentEvent) -> None:
        if isinstance(event, HandStartEvent):
            self._queued_phases.clear()
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
            self._queued_phases.append(event)
            return

        elif isinstance(event, ActionEvent):
            self._flush_queued_phases()
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
            self._flush_queued_phases()
            for r in event.results:
                cards = " ".join(r.get("cards", []))
                hand = r.get("hand", "")
                won = r.get("winnings", 0)
                marker = "★" if won > 0 else " "
                self._action_feed.add(f"{marker} {r['player']}", f"{cards} → {hand}")

        elif isinstance(event, HandEndEvent):
            self._flush_queued_phases()
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
        self._dirty = True

    def paint(self) -> None:
        if self._live is not None and self._dirty:
            self._live.update(self.build_layout())
            self._live.refresh()
            self._dirty = False

    def _sync_chips_from_engine(self) -> None:
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
        player_list = list(self._player_state.values())
        self._table_view.update_players(player_list)

        standings = [{"name": ps["name"], "chips": ps["chips"]} for ps in player_list]
        self._stats.update(
            standings,
            blind_level=self._current_blind,
            hands_played=self._hands_played,
        )

    def _layout_sizes(self) -> tuple[int, int, int]:
        terminal_height = max(22, self._console.size.height - 1)
        if terminal_height >= 38:
            middle_size = 10
            stats_size = 10
            table_size = max(18, terminal_height - middle_size - stats_size)
            return table_size, middle_size, stats_size
        if terminal_height >= 30:
            middle_size = 8
            stats_size = 7
        else:
            middle_size = 6
            stats_size = 6
        table_size = max(10, terminal_height - middle_size - stats_size)
        return table_size, middle_size, stats_size

    def build_layout(self) -> Layout:
        table_size, middle_size, stats_size = self._layout_sizes()

        layout = Layout()
        layout.split_column(
            Layout(name="table", size=table_size),
            Layout(name="middle", size=middle_size),
            Layout(name="stats", size=stats_size),
        )
        layout["middle"].split_row(
            Layout(name="actions", ratio=2),
            Layout(name="chat", ratio=2),
            Layout(name="thoughts", ratio=2),
        )
        layout["table"].update(self._table_view.render(height=table_size))
        layout["actions"].update(self._action_feed.render(height=middle_size))
        layout["chat"].update(self._chat.render(height=middle_size))
        layout["thoughts"].update(self._commentary.render(height=middle_size))
        layout["stats"].update(self._stats.render(height=stats_size))
        return layout

    async def run(self) -> TournamentResult:
        self._sync_chips_from_engine()
        self._push_state_to_views()

        tournament_task = asyncio.create_task(self._director.run())

        with Live(
            self.build_layout(),
            auto_refresh=False,
            screen=False,
            console=self._console,
        ) as live:
            self._live = live
            while not tournament_task.done():
                self.paint()
                await asyncio.sleep(0.1)
            self.paint()
            await asyncio.sleep(0.5)
        self._live = None

        return await tournament_task
