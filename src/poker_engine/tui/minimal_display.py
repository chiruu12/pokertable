"""Minimal CLI display -- cards, actions, results. No commentary or thinking.

Same interface as ConsoleDisplay and PokerTUI: subscribes to the EventBus,
runs the tournament via director.run(), prints final standings.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

from poker_engine.tournament.director import TournamentDirector, TournamentResult
from poker_engine.tournament.events import (
    ActionEvent,
    BlindLevelEvent,
    CardsDealtEvent,
    EliminationEvent,
    HandEndEvent,
    HandStartEvent,
    PhaseChangeEvent,
    ShowdownEvent,
    TournamentEvent,
)
from poker_engine.tui.card_display import SUIT_STYLES

ACTION_STYLES = {
    "fold": "red",
    "call": "green",
    "check": "dim green",
    "raise": "yellow",
    "all_in": "bold magenta",
}

MAX_NAME = 10


def _color_card(c: str) -> str:
    for suit, style in SUIT_STYLES.items():
        if suit in c:
            return f"[{style}]{c}[/{style}]"
    return c


def _color_cards(cards: list[str]) -> str:
    return " ".join(_color_card(c) for c in cards)


class MinimalDisplay:
    """Lean CLI output -- hand flow and results only."""

    def __init__(
        self,
        director: TournamentDirector,
        console: Console | None = None,
    ) -> None:
        self._director = director
        self._console = console or Console()
        self._current_blind: dict[str, int] = {"sb": 10, "bb": 20}

        self._director.event_bus.subscribe(self._handle_event)

    def _handle_event(self, event: TournamentEvent) -> None:
        c = self._console

        if isinstance(event, HandStartEvent):
            c.print()
            c.rule(
                f"[bold cyan]Hand #{event.hand_num}[/bold cyan]  "
                f"Dealer: {event.dealer}  "
                f"Blinds: {self._current_blind['sb']}/{self._current_blind['bb']}"
            )

        elif isinstance(event, CardsDealtEvent):
            for name, cards in event.hands.items():
                c.print(f"  [dim]Dealt[/dim]  {name_pad(name)}:  {_color_cards(cards)}")

        elif isinstance(event, PhaseChangeEvent):
            c.print(f"\n  [bold yellow]{event.phase}[/bold yellow]  {_color_cards(event.community)}")

        elif isinstance(event, ActionEvent):
            style = ACTION_STYLES.get(event.action, "white")
            amt = ""
            if event.action == "raise" and event.amount:
                amt = f" to ${event.amount}"
            elif event.action == "all_in":
                amt = " ALL-IN"
            c.print(
                f"    [{style}]{name_pad(event.player)}: "
                f"{event.action}{amt}[/{style}]"
                f"  [dim]pot ${event.pot}[/dim]"
            )

        elif isinstance(event, ShowdownEvent):
            c.print()
            for r in event.results:
                cards = _color_cards(r["cards"])
                won = r["winnings"]
                marker = "[bold green] ★[/bold green]" if won > 0 else "  "
                c.print(
                    f"  {marker} {name_pad(r['player'])}:  {cards}  "
                    f"->  [bold]{r['hand']}[/bold]"
                )

        elif isinstance(event, HandEndEvent):
            winners = ", ".join(event.winners)
            if event.win_reason == "all_folded":
                c.print(f"\n  [bold green]>>> {winners} wins (everyone folded)[/bold green]")
            else:
                c.print(f"\n  [bold green]>>> {winners} wins[/bold green]")

        elif isinstance(event, BlindLevelEvent):
            self._current_blind["sb"] = event.small_blind
            self._current_blind["bb"] = event.big_blind

        elif isinstance(event, EliminationEvent):
            c.print(f"  [bold red]💀 {event.player} eliminated (#{event.position})[/bold red]")

    async def run(self) -> TournamentResult:
        result = await self._director.run()
        self._print_standings(result)
        return result

    def _print_standings(self, result: TournamentResult) -> None:
        c = self._console
        c.print()
        c.rule("[bold]Final Standings[/bold]")

        table = Table(show_header=True, header_style="bold", padding=(0, 1))
        table.add_column("#", style="dim", width=3)
        table.add_column("Player", style="cyan", width=MAX_NAME)
        table.add_column("Chips", justify="right", style="green")
        table.add_column("Won", justify="right")
        table.add_column("Played", justify="right")
        table.add_column("", width=20)

        max_chips = max((s["chips"] for s in result.standings), default=1) or 1
        bar_width = 16
        for i, s in enumerate(result.standings, 1):
            filled = int(bar_width * s["chips"] / max_chips)
            bar = f"[green]{'█' * filled}[/green]{'░' * (bar_width - filled)}"
            table.add_row(
                str(i),
                s["name"],
                f"${s['chips']:,}",
                str(s["hands_won"]),
                str(s["hands_played"]),
                bar,
            )
        c.print(table)
        c.print(f"\n[dim]{result.hands_played} hands played[/dim]")


def name_pad(name: str) -> str:
    truncated = name[:MAX_NAME] if len(name) > MAX_NAME else name
    return f"{truncated:>{MAX_NAME}}"
