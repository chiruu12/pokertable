"""Commentary panel showing LLM agent reasoning."""

from __future__ import annotations

from collections import deque
from textwrap import shorten

from rich.panel import Panel
from rich.text import Text

MAX_LINE_LEN = 72
MAX_NAME_LEN = 14


class CommentaryPanel:
    """Displays LLM commentary/reasoning from poker agents."""

    def __init__(self, maxlen: int = 8) -> None:
        self._entries: deque[Text] = deque(maxlen=maxlen)

    def add(self, player: str, text: str) -> None:
        """Add a commentary entry.

        Args:
            player: Player name who generated the thought.
            text: Commentary text (truncated to 72 chars).
        """
        truncated = text[:MAX_LINE_LEN] + "..." if len(text) > MAX_LINE_LEN else text
        line = Text()
        short_name = shorten(player, width=MAX_NAME_LEN, placeholder="...")
        line.append(f"{short_name}: ", style="bold cyan")
        line.append(truncated, style="italic")
        self._entries.append(line)

    def render(self, height: int | None = None) -> Panel:
        """Render the commentary panel."""
        content = Text()
        max_rows = max(1, (height or 10) - 2)
        entries = list(self._entries)[-max_rows:]

        for i, entry in enumerate(entries):
            if i > 0:
                content.append("\n")
            content.append_text(entry)

        if not self._entries:
            content.append("Waiting for agent thoughts...", style="dim italic")

        return Panel(
            content,
            title="[bold]Agent Thoughts[/bold]",
            border_style="cyan",
            height=height or 10,
        )
