"""Rich console display — prints events inline (no Live dashboard).

Use this when you want visible output in a terminal without the
full-screen TUI layout. Subscribes to the same EventBus as PokerTUI.
"""

from __future__ import annotations

from textwrap import shorten

from rich.console import Console
from rich.markup import escape
from rich.table import Table

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
from poker_engine.tui.card_display import SUIT_STYLES

ACTION_STYLES = {
    "fold": "red",
    "call": "green",
    "check": "dim green",
    "raise": "yellow",
    "all_in": "bold magenta",
}

MAX_NAME_LEN = 14
MAX_MESSAGE_LEN = 88


def _color_card(c: str) -> str:
    for suit, style in SUIT_STYLES.items():
        if suit in c:
            return f"[{style}]{c}[/{style}]"
    return c


def _color_cards(cards: list[str]) -> str:
    return " ".join(_color_card(c) for c in cards)


def _short(text: str, width: int) -> str:
    return shorten(" ".join(text.split()), width=width, placeholder="...")


def _name(text: str) -> str:
    return _short(text, MAX_NAME_LEN)


class ConsoleDisplay:
    """Inline Rich console display for poker tournaments.

    Prints each event as it happens — no full-screen layout, works
    in any terminal including piped output and CI logs.
    """

    def __init__(
        self,
        director: TournamentDirector,
        console: Console | None = None,
    ) -> None:
        self._director = director
        self._console = console or Console()
        self._current_blind = {"sb": 10, "bb": 20}

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
                padded = f"{_name(name):>{MAX_NAME_LEN}}"
                c.print(f"  [dim]Dealt[/dim]  {padded}:  {_color_cards(cards)}")

        elif isinstance(event, PhaseChangeEvent):
            cards = _color_cards(event.community)
            c.print(f"\n  [bold yellow]{'─' * 3} {event.phase} {'─' * 3}[/bold yellow]  {cards}")

        elif isinstance(event, ActionEvent):
            style = ACTION_STYLES.get(event.action, "white")
            amt = ""
            if event.action == "raise" and event.amount:
                amt = f" to ${event.amount}"
            elif event.action == "all_in":
                amt = " ALL-IN"
            c.print(
                f"    [{style}]{_name(event.player):>{MAX_NAME_LEN}}: "
                f"{event.action}{amt}[/{style}]"
                f"  [dim]pot ${event.pot}[/dim]"
            )

        elif isinstance(event, CommentaryEvent):
            short = _short(event.text, MAX_MESSAGE_LEN)
            c.print(f"    [dim italic]thought {_name(event.player)}: {escape(short)}[/dim italic]")

        elif isinstance(event, ShowdownEvent):
            c.print()
            for r in event.results:
                cards = _color_cards(r["cards"])
                hand = r["hand"]
                player = r["player"]
                won = r["winnings"]
                marker = "[bold green] ★[/bold green]" if won > 0 else "  "
                padded = f"{_name(player):>{MAX_NAME_LEN}}"
                c.print(f"  {marker} {padded}:  {cards}  ->  [bold]{hand}[/bold]")

        elif isinstance(event, HandEndEvent):
            winners = ", ".join(event.winners)
            if event.win_reason == "all_folded":
                c.print(f"\n  [bold green]>>> {winners} wins (everyone folded)[/bold green]")
            else:
                c.print(f"\n  [bold green]>>> {winners} wins[/bold green]")

        elif isinstance(event, BlindLevelEvent):
            self._current_blind["sb"] = event.small_blind
            self._current_blind["bb"] = event.big_blind

        elif isinstance(event, TableTalkEvent):
            message = _short(event.message, MAX_MESSAGE_LEN)
            player = _name(event.player)
            c.print(f'    [magenta]{player}:[/magenta] [italic]"{escape(message)}"[/italic]')

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
        table.add_column("Player", style="cyan", width=10)
        table.add_column("Chips", justify="right", style="green")
        table.add_column("Won", justify="right")
        table.add_column("Played", justify="right")
        table.add_column("", width=22)

        max_chips = max((s["chips"] for s in result.standings), default=1) or 1
        for i, s in enumerate(result.standings, 1):
            bar_len = int(18 * s["chips"] / max_chips)
            bar = "█" * bar_len + "░" * (18 - bar_len)
            table.add_row(
                str(i),
                s["name"],
                f"${s['chips']:,}",
                str(s["hands_won"]),
                str(s["hands_played"]),
                f"[green]{bar}[/green]",
            )
        c.print(table)
        c.print(f"\n[dim]{result.hands_played} hands played[/dim]")

        if result.payouts:
            c.print("\n[bold]Payouts:[/bold]")
            for p in result.payouts:
                c.print(f"  #{p['place']}: {p['player']} — ${p['amount']:,}")
