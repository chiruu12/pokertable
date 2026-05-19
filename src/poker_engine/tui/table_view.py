"""ASCII poker table renderer that adapts from 2-9 players."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.text import Text

from poker_engine.tui.card_display import render_hand

# Player box width (characters inside border, total ~14 with borders)
BOX_W = 12
# Total table width in characters
TABLE_W = 56

# Seat layout definitions per player count.
# Each layout is a list of rows; each row is a list of seat indices.
# None means the center (pot/community) goes in that row position.
# Rows are rendered top to bottom.
#
# Layout strategy:
#   - top row: seats across the top
#   - middle row: left seat(s) + center + right seat(s)
#   - bottom row: seats across the bottom
#
# Seat 0 is always bottom-center (the "hero" position).

SEAT_LAYOUTS: dict[int, list[list[int | None]]] = {
    2: [
        [1],       # top
        [None],    # center
        [0],       # bottom
    ],
    3: [
        [None],    # center (top)
        [1, 2],    # middle sides
        [0],       # bottom
    ],
    4: [
        [2, 3],    # top
        [1, None, None],  # middle-left + center
        [0, None, None],  # bottom-left (special: right empty)
    ],
    5: [
        [2, 3],    # top
        [1, 4],    # middle sides
        [0],       # bottom center (seat 5 doesn't exist for 5)
    ],
    6: [
        [2, 3],    # top
        [1, 4],    # middle sides
        [0, 5],    # bottom
    ],
    7: [
        [3, 4],      # top
        [2, 5],      # middle sides
        [0, 1, 6],   # bottom
    ],
    8: [
        [3, 4, 5],   # top
        [2, 6],      # middle sides
        [0, 1, 7],   # bottom
    ],
    9: [
        [3, 4, 5],   # top
        [2, 6],      # middle sides
        [0, 1, 7, 8],  # bottom
    ],
}


def _make_player_box(player: dict[str, Any] | None) -> list[str]:
    """Build a 3-line player box (each line BOX_W wide).

    Returns list of 3 strings, each exactly BOX_W characters.
    """
    if player is None:
        blank = " " * BOX_W
        return [blank, blank, blank]

    name = player["name"]
    chips = player["chips"]
    tag = player.get("position_tag", "")
    is_active = player.get("is_active", False)
    folded = player.get("folded", False)

    # Format name line
    if tag:
        name_line = f"{name} [{tag}]"
    else:
        name_line = name

    chip_line = f"${chips:,}"

    # Truncate to fit
    name_line = name_line[:BOX_W]
    chip_line = chip_line[:BOX_W]

    # Center each line within BOX_W
    name_line = name_line.center(BOX_W)
    chip_line = chip_line.center(BOX_W)
    border_top = "┌" + "─" * BOX_W + "┐"
    border_bot = "└" + "─" * BOX_W + "┘"

    # Apply styling via Rich markup
    if folded:
        name_line = f"[dim]{name_line}[/dim]"
        chip_line = f"[dim]{chip_line}[/dim]"
    elif is_active:
        name_line = f"[bold bright_green]{name_line}[/bold bright_green]"
        chip_line = f"[bright_green]{chip_line}[/bright_green]"

    return [
        border_top,
        f"│{name_line}│",
        f"│{chip_line}│",
        border_bot,
    ]


def _make_center_box(
    community: list[str], pot: int, hand_num: int
) -> list[str]:
    """Build the center community-card / pot display."""
    inner_w = 20

    cards_str = render_hand(community) if community else "[dim]-- -- -- -- --[/dim]"
    pot_str = f"Pot: ${pot:,}"
    hand_str = f"Hand #{hand_num}"

    border_top = "┌" + "─" * inner_w + "┐"
    border_bot = "└" + "─" * inner_w + "┘"

    return [
        border_top,
        f"│{hand_str:^{inner_w}}│",
        f"│{cards_str:^{inner_w}}│",
        f"│{pot_str:^{inner_w}}│",
        border_bot,
    ]


class TableView:
    """Renders the poker table with player seats around an oval."""

    def __init__(self) -> None:
        self._players: list[dict[str, Any]] = []
        self._community: list[str] = []
        self._pot: int = 0
        self._hand_num: int = 0

    def update_players(self, players: list[dict[str, Any]]) -> None:
        """Update player info.

        Args:
            players: List of dicts with keys: name, chips,
                     position_tag, is_active, folded.
        """
        self._players = list(players)

    def update_community(self, cards: list[str]) -> None:
        """Update community cards."""
        self._community = list(cards)

    def update_pot(self, pot: int) -> None:
        """Update the current pot size."""
        self._pot = pot

    def update_hand_num(self, hand_num: int) -> None:
        """Update the current hand number."""
        self._hand_num = hand_num

    def render(self) -> Panel:
        """Render the full table as a Rich Panel."""
        n = len(self._players)
        if n < 2:
            n = 2  # Minimum for layout lookup

        layout_key = min(n, 9)
        layout = SEAT_LAYOUTS[layout_key]
        center_box = _make_center_box(
            self._community, self._pot, self._hand_num
        )

        lines: list[str] = []

        for row_idx, seat_indices in enumerate(layout):
            row_lines = self._render_row(
                seat_indices, center_box, row_idx, layout
            )
            lines.extend(row_lines)

        content = Text.from_markup("\n".join(lines))
        return Panel(
            content,
            title="[bold green]♠ ♥ Poker Table ♦ ♣[/bold green]",
            border_style="green",
            height=16,
        )

    def _render_row(
        self,
        seat_indices: list[int | None],
        center_box: list[str],
        row_idx: int,
        layout: list[list[int | None]],
    ) -> list[str]:
        """Render one row of the table layout.

        For 3-player layout, the center is in the top row and sides
        are in the middle row. For other layouts, the center is
        always shown in the middle row (row_idx == 1).
        """
        n = len(self._players)
        layout_key = min(max(n, 2), 9)
        is_middle = row_idx == 1

        # Special case: 3-player has center at top
        if layout_key == 3 and row_idx == 0:
            return self._render_center_row([], center_box)
        if layout_key == 3 and row_idx == 1:
            return self._render_sides_row(seat_indices, center_box)

        # Special case: 4-player compact layout
        if layout_key == 4:
            return self._render_4p_row(
                seat_indices, center_box, row_idx
            )

        # Standard layouts (2, 5-9)
        if layout_key == 2:
            if row_idx == 1:
                return self._render_center_row([], center_box)
            return self._render_seat_row(seat_indices)

        if is_middle:
            return self._render_sides_row(seat_indices, center_box)
        return self._render_seat_row(seat_indices)

    def _get_player(self, idx: int) -> dict[str, Any] | None:
        """Safely get a player by seat index."""
        if 0 <= idx < len(self._players):
            return self._players[idx]
        return None

    def _render_seat_row(
        self, seat_indices: list[int | None]
    ) -> list[str]:
        """Render a row of player boxes centered on the table."""
        boxes = []
        for idx in seat_indices:
            if idx is not None:
                boxes.append(_make_player_box(self._get_player(idx)))

        if not boxes:
            return []

        # Each box is 4 lines (border_top, name, chips, border_bot)
        # Total box width = BOX_W + 2 (for │ borders)
        full_box_w = BOX_W + 2
        gap = 2
        total_w = len(boxes) * full_box_w + (len(boxes) - 1) * gap
        left_pad = max(0, (TABLE_W - total_w) // 2)

        result: list[str] = []
        num_lines = len(boxes[0])
        for line_idx in range(num_lines):
            parts = []
            for b_idx, box in enumerate(boxes):
                if b_idx > 0:
                    parts.append(" " * gap)
                parts.append(box[line_idx])
            row_str = " " * left_pad + "".join(parts)
            result.append(row_str)
        return result

    def _render_center_row(
        self,
        _seat_indices: list[int | None],
        center_box: list[str],
    ) -> list[str]:
        """Render just the center box, centered."""
        result: list[str] = []
        for line in center_box:
            # Center the line within TABLE_W
            # strip markup for measuring would be complex;
            # approximate with raw len since box borders are ASCII
            padded = line.center(TABLE_W)
            result.append(padded)
        return result

    def _render_sides_row(
        self,
        seat_indices: list[int | None],
        center_box: list[str],
    ) -> list[str]:
        """Render left seat + center + right seat."""
        left_player = (
            self._get_player(seat_indices[0]) if seat_indices else None
        )
        right_player = (
            self._get_player(seat_indices[1])
            if len(seat_indices) > 1
            else None
        )

        left_box = _make_player_box(left_player)
        right_box = _make_player_box(right_player)

        # Build composite lines
        # left_box is 4 lines, center is 5 lines, right is 4 lines
        # Pad shorter ones
        max_lines = max(len(left_box), len(center_box), len(right_box))
        while len(left_box) < max_lines:
            left_box.insert(0, " " * BOX_W)
        while len(right_box) < max_lines:
            right_box.insert(0, " " * BOX_W)
        while len(center_box) < max_lines:
            center_box.insert(0, " " * 22)

        full_box_w = BOX_W + 2  # with borders
        center_w = 22  # 20 inner + 2 borders
        gap = 2
        total_w = full_box_w * 2 + center_w + gap * 2
        left_pad = max(0, (TABLE_W - total_w) // 2)

        result: list[str] = []
        for i in range(max_lines):
            left = left_box[i] if left_player else " " * full_box_w
            right = right_box[i] if right_player else " " * full_box_w
            center = center_box[i]
            line = (
                " " * left_pad
                + left + " " * gap + center + " " * gap + right
            )
            result.append(line)
        return result

    def _render_4p_row(
        self,
        seat_indices: list[int | None],
        center_box: list[str],
        row_idx: int,
    ) -> list[str]:
        """Handle the 4-player layout rows."""
        if row_idx == 0:
            # Top: seats 2 and 3
            real = [i for i in seat_indices if i is not None]
            return self._render_seat_row(real)
        if row_idx == 1:
            # Middle: seat 1 + center
            return self._render_sides_row([1, None], center_box)
        # Bottom: seat 0
        return self._render_seat_row([0])
