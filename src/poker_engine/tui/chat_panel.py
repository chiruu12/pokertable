"""Chat panel showing table talk between players."""

from __future__ import annotations

from collections import deque
from textwrap import shorten

from rich.panel import Panel
from rich.text import Text

MAX_NAME_LEN = 14


class ChatPanel:
    """Displays table talk messages from players."""

    def __init__(self, maxlen: int = 12) -> None:
        self._entries: deque[Text] = deque(maxlen=maxlen)

    def add(self, player: str, message: str) -> None:
        truncated = message[:72] + "..." if len(message) > 72 else message
        line = Text()
        short_name = shorten(player, width=MAX_NAME_LEN, placeholder="...")
        line.append(f"{short_name}: ", style="bold cyan")
        line.append(truncated)
        self._entries.append(line)

    def render(self, height: int | None = None) -> Panel:
        content = Text()
        max_rows = max(1, (height or 10) - 2)
        entries = list(self._entries)[-max_rows:]

        for i, entry in enumerate(entries):
            if i > 0:
                content.append("\n")
            content.append_text(entry)

        if not self._entries:
            content.append("No table talk yet...", style="dim italic")

        return Panel(
            content,
            title="[bold]Table Talk[/bold]",
            border_style="magenta",
            height=height or 10,
        )
