"""Card rendering with Unicode suits and Rich markup."""

from __future__ import annotations

RED_SUITS = {"♥", "♦"}


def render_card(card_str: str, face_down: bool = False) -> str:
    """Render a single card string with Rich markup.

    Args:
        card_str: Card like "A♠" or "K♥".
        face_down: If True, returns a hidden card placeholder.

    Returns:
        Rich-markup string.
    """
    if face_down:
        return "[dim]??[/dim]"

    # Determine suit character (last char)
    suit_char = card_str[-1] if card_str else ""
    if suit_char in RED_SUITS:
        return f"[red]{card_str}[/red]"
    return f"[white]{card_str}[/white]"


def render_hand(cards: list[str]) -> str:
    """Render multiple cards separated by spaces.

    Args:
        cards: List of card strings like ["A♠", "K♥"].

    Returns:
        Rich-markup string of all cards.
    """
    return " ".join(render_card(c) for c in cards)
