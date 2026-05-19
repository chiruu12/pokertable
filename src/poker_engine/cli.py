"""Command-line interface for the poker engine."""

from __future__ import annotations

import asyncio
import re
from typing import Optional

import typer

app = typer.Typer(
    name="poker",
    help="Texas Hold'em poker engine — tournaments, equity, and more.",
    no_args_is_help=True,
)


@app.command()
def play(
    config: Optional[str] = typer.Argument(  # noqa: UP007
        None, help="Path to tournament YAML config file."
    ),
) -> None:
    """Run a tournament from a YAML config file."""
    if config:
        typer.echo(f"Starting tournament from config: {config}")
    else:
        typer.echo("Starting tournament...")


@app.command()
def quick(
    players: int = typer.Option(4, "--players", "-n", help="Number of random bots."),
    hands: int = typer.Option(50, "--hands", "-h", help="Maximum hands to play."),
    chips: int = typer.Option(1000, "--chips", "-c", help="Starting chips per player."),
    seed: Optional[int] = typer.Option(None, "--seed", "-s", help="Random seed."),  # noqa: UP007
) -> None:
    """Quick-start a tournament with N random bots."""
    asyncio.run(_run_quick(players, hands, chips, seed))


async def _run_quick(
    num_players: int,
    max_hands: int,
    starting_chips: int,
    seed: int | None,
) -> None:
    """Run a quick tournament with random players."""
    from poker_engine.players.random_player import RandomPlayer
    from poker_engine.tournament.blind_schedule import BlindSchedule
    from poker_engine.tournament.director import TournamentDirector

    bot_players = [
        RandomPlayer(name=f"Bot-{i + 1}", seed=seed + i if seed is not None else None)
        for i in range(num_players)
    ]

    schedule = BlindSchedule.turbo()
    director = TournamentDirector(
        players=bot_players,
        blind_schedule=schedule,
        starting_chips=starting_chips,
        seed=seed,
        max_hands=max_hands,
    )

    typer.echo(f"Starting quick tournament: {num_players} bots, {starting_chips} chips each")
    typer.echo(f"Max hands: {max_hands}, Blind structure: turbo")
    typer.echo("-" * 50)

    result = await director.run()

    typer.echo(f"\nTournament complete! Hands played: {result.hands_played}")
    typer.echo("-" * 50)

    if result.standings:
        typer.echo("\nFinal Standings:")
        for i, p in enumerate(result.standings, 1):
            typer.echo(
                f"  {i}. {p['name']}: {p['chips']} chips "
                f"({p['hands_won']}/{p['hands_played']} hands won)"
            )

    if result.payouts:
        typer.echo("\nPayouts:")
        for payout in result.payouts:
            typer.echo(f"  #{payout['place']}: {payout['player']} — {payout['amount']} chips")


def _parse_card_str(card_str: str) -> tuple[int, int]:
    """Parse a card string like 'As' or '10h' into (rank, suit_index).

    Returns (rank_int, suit_int) where suit_int maps to Suit enum values.
    """
    from poker_engine.core.cards import Suit

    suit_map = {"s": Suit.SPADES, "h": Suit.HEARTS, "d": Suit.DIAMONDS, "c": Suit.CLUBS}
    rank_map = {
        "2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9,
        "10": 10, "T": 10, "t": 10, "J": 11, "j": 11, "Q": 12, "q": 12,
        "K": 13, "k": 13, "A": 14, "a": 14,
    }

    match = re.match(r"^(10|[2-9TtJjQqKkAa])([SsHhDdCc])$", card_str)
    if not match:
        raise typer.BadParameter(f"Invalid card: {card_str!r}. Use format like As, Kh, 10d, 2c.")

    rank_str = match.group(1)
    suit_char = match.group(2).lower()
    rank = rank_map[rank_str]
    suit = suit_map[suit_char]
    return rank, suit


@app.command()
def equity(
    cards: list[str] = typer.Argument(  # noqa: UP006
        ..., help="Hole cards, e.g. 'As Kh' or 'AsTd'."
    ),
    opponents: int = typer.Option(1, "--opponents", "-o", help="Number of opponents."),
    simulations: int = typer.Option(
        2000, "--simulations", "-n", help="Monte Carlo simulations."
    ),
) -> None:
    """Calculate hand equity from the command line.

    Pass two hole cards like: poker equity As Kh --opponents 2
    """
    from poker_engine.core.cards import Card

    # Handle case where cards are passed as a single string like "AsKh"
    raw_cards: list[str] = []
    for c in cards:
        if len(c) == 4 and re.match(r"^[2-9TtJjQqKkAa][SsHhDdCc]{2}", c):
            # Could be two cards concatenated like "AsKh"
            raw_cards.append(c[:2])
            raw_cards.append(c[2:])
        elif len(c) == 5 and c[:2] == "10":
            # "10sKh" type concat
            raw_cards.append(c[:3])
            raw_cards.append(c[3:])
        else:
            raw_cards.append(c)

    if len(raw_cards) != 2:
        typer.echo(f"Error: Expected 2 hole cards, got {len(raw_cards)}.", err=True)
        raise typer.Exit(code=1)

    parsed = []
    for rc in raw_cards:
        rank, suit = _parse_card_str(rc)
        parsed.append(Card(rank=rank, suit=suit))

    from poker_engine.equity.monte_carlo import calculate_equity_v2

    result = calculate_equity_v2(
        hole_cards=parsed,
        community_cards=[],
        num_opponents=opponents,
        num_simulations=simulations,
    )

    typer.echo(f"Hand: {parsed[0]} {parsed[1]}")
    typer.echo(f"Opponents: {opponents}")
    typer.echo(f"Win probability: {result.win_probability:.1%}")
    typer.echo(f"Tie probability: {result.tie_probability:.1%}")
    if result.hand_improvement:
        typer.echo("Hand distribution:")
        for name, prob in result.hand_improvement.items():
            typer.echo(f"  {name}: {prob:.1%}")


if __name__ == "__main__":
    app()
