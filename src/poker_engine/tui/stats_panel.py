"""Stats panel with chip standings and blind level."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table

BAR_WIDTH = 20


class StatsPanel:
    """Displays player chip standings with visual bars and blind info."""

    def __init__(self) -> None:
        self._standings: list[dict[str, Any]] = []
        self._blind_level: dict[str, Any] | None = None
        self._hands_played: int = 0

    def update(
        self,
        standings: list[dict[str, Any]],
        blind_level: dict[str, Any] | None = None,
        hands_played: int = 0,
    ) -> None:
        """Update standings data.

        Args:
            standings: List of dicts with 'name' and 'chips' keys.
            blind_level: Dict with 'level', 'small_blind', 'big_blind', 'ante'.
            hands_played: Total hands played so far.
        """
        self._standings = sorted(standings, key=lambda s: s["chips"], reverse=True)
        self._blind_level = blind_level
        self._hands_played = hands_played

    def render(self) -> Panel:
        """Render the stats panel with a chip-bar table."""
        table = Table(expand=True, show_header=True, header_style="bold")
        table.add_column("Player", style="bold", ratio=2)
        table.add_column("Chips", justify="right", ratio=1)
        table.add_column("Bar", ratio=3)

        max_chips = max((s["chips"] for s in self._standings), default=1)
        max_chips = max(max_chips, 1)

        for s in self._standings:
            chips = s["chips"]
            name = s["name"]
            filled = int((chips / max_chips) * BAR_WIDTH)
            bar = "[green]" + "█" * filled + "[/green]"
            bar += "[dim]" + "░" * (BAR_WIDTH - filled) + "[/dim]"
            style = "dim" if chips == 0 else ""
            table.add_row(name, f"${chips:,}", bar, style=style)

        # Build subtitle with blind and hand info
        subtitle_parts: list[str] = []
        if self._blind_level:
            bl = self._blind_level
            sb, bb = bl["small_blind"], bl["big_blind"]
            ante_str = f" ante {bl['ante']}" if bl.get("ante") else ""
            subtitle_parts.append(
                f"Blinds: ${sb:,}/${bb:,}{ante_str} (Lvl {bl['level']})"
            )
        subtitle_parts.append(f"Hands: {self._hands_played}")
        subtitle = "  |  ".join(subtitle_parts)

        return Panel(
            table,
            title="[bold]Standings[/bold]",
            subtitle=subtitle,
            border_style="yellow",
        )
