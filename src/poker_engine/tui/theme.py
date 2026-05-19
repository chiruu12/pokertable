"""Color constants and styles for the poker TUI."""

CARD_RED = "red"
CARD_WHITE = "white"

ACTION_COLORS: dict[str, str] = {
    "fold": "red",
    "call": "green",
    "check": "dim green",
    "raise": "yellow",
    "all_in": "bold magenta",
}

ACTIVE_BORDER = "bright_green"
INACTIVE_BORDER = "dim"
