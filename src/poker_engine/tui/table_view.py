"""ASCII poker table renderer that adapts from 2-9 players."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.text import Text

BOX_W = 14
CENTER_W = 28
TABLE_W = 66

SEAT_LAYOUTS: dict[int, list[list[int | None]]] = {
    2: [[1], [None], [0]],
    3: [[None], [1, 2], [0]],
    4: [[2, 3], [1, None], [0]],
    5: [[2, 3], [1, 4], [0]],
    6: [[2, 3], [1, 4], [0, 5]],
    7: [[3, 4], [2, 5], [0, 1, 6]],
    8: [[3, 4, 5], [2, 6], [0, 1, 7]],
    9: [[3, 4, 5], [2, 6], [0, 1, 7, 8]],
}

SUIT_STYLES = {"♥": "bold red", "♦": "bold red", "♠": "bold blue", "♣": "bold blue"}


def _pad_center(text: str, width: int) -> str:
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return " " * pad + text + " " * (width - len(text) - pad)


def _color_card(c: str) -> str:
    for suit, style in SUIT_STYLES.items():
        if suit in c:
            return f"[{style}]{c}[/{style}]"
    return c


def _color_cards_inline(cards: list[str]) -> str:
    return " ".join(_color_card(c) for c in cards)


def _color_cards_padded(cards: list[str], width: int) -> str:
    plain = " ".join(cards)
    rich = _color_cards_inline(cards)
    pad = max(0, (width - len(plain)) // 2)
    fill = max(0, width - pad - len(plain))
    return " " * pad + rich + " " * fill


def _make_player_box(player: dict[str, Any] | None) -> list[str]:
    full_w = BOX_W + 2
    if player is None:
        blank = " " * full_w
        return [blank, blank, blank, blank, blank]

    name = player["name"]
    chips = player["chips"]
    tag = player.get("position_tag", "")
    is_active = player.get("is_active", False)
    folded = player.get("folded", False)
    hole_cards = player.get("hole_cards", [])

    name_str = f"{name} [{tag}]" if tag else name
    chip_str = f"${chips:,}"

    if hole_cards:
        cards_plain = " ".join(hole_cards)
        cards_rich = _color_cards_inline(hole_cards)
    else:
        cards_plain = "?? ??"
        cards_rich = "[dim]?? ??[/dim]"

    name_str = _pad_center(name_str[:BOX_W], BOX_W)
    chip_str = _pad_center(chip_str[:BOX_W], BOX_W)
    cards_pad = max(0, (BOX_W - len(cards_plain)) // 2)
    cards_fill = max(0, BOX_W - cards_pad - len(cards_plain))
    cards_line = " " * cards_pad + cards_rich + " " * cards_fill

    if folded:
        name_str = f"[dim]{name_str}[/dim]"
        chip_str = f"[dim]{chip_str}[/dim]"
        cards_line = f"[dim]{_pad_center('folded', BOX_W)}[/dim]"
    elif is_active:
        name_str = f"[bold bright_green]{name_str}[/bold bright_green]"
        chip_str = f"[bright_green]{chip_str}[/bright_green]"

    border = "─" * BOX_W
    return [
        f"┌{border}┐",
        f"│{name_str}│",
        f"│{chip_str}│",
        f"│{cards_line}│",
        f"└{border}┘",
    ]


def _make_center_box(community: list[str], pot: int, hand_num: int) -> list[str]:
    n = len(community)
    if n == 0:
        phase = "Pre-Flop"
        cards_plain = "─   ─   ─   ─   ─"
        cards_rich = f"[dim]{cards_plain}[/dim]"
    elif n == 3:
        phase = "Flop"
        cards_plain = " ".join(community) + "   ─   ─"
        cards_rich = _color_cards_inline(community) + "   [dim]─   ─[/dim]"
    elif n == 4:
        phase = "Turn"
        cards_plain = " ".join(community) + "   ─"
        cards_rich = _color_cards_inline(community) + "   [dim]─[/dim]"
    else:
        phase = "River"
        cards_plain = " ".join(community)
        cards_rich = _color_cards_inline(community)

    title = f"Hand #{hand_num} · {phase}"
    pot_str = f"Pot: ${pot:,}"

    title_line = _pad_center(title, CENTER_W)
    pot_line = _pad_center(pot_str, CENTER_W)

    cards_pad = max(0, (CENTER_W - len(cards_plain)) // 2)
    cards_fill = max(0, CENTER_W - cards_pad - len(cards_plain))
    cards_line = " " * cards_pad + cards_rich + " " * cards_fill

    border = "─" * CENTER_W
    return [
        f"┌{border}┐",
        f"│{title_line}│",
        f"│{cards_line}│",
        f"│{pot_line}│",
        f"└{border}┘",
    ]


class TableView:
    """Renders the poker table with player seats around an oval."""

    def __init__(self) -> None:
        self._players: list[dict[str, Any]] = []
        self._community: list[str] = []
        self._pot: int = 0
        self._hand_num: int = 0

    def update_players(self, players: list[dict[str, Any]]) -> None:
        self._players = list(players)

    def update_community(self, cards: list[str]) -> None:
        self._community = list(cards)

    def update_pot(self, pot: int) -> None:
        self._pot = pot

    def update_hand_num(self, hand_num: int) -> None:
        self._hand_num = hand_num

    def render(self) -> Panel:
        n = max(len(self._players), 2)
        layout_key = min(n, 9)
        layout = SEAT_LAYOUTS[layout_key]
        center = _make_center_box(self._community, self._pot, self._hand_num)

        lines: list[str] = []
        for row_idx, seat_indices in enumerate(layout):
            is_middle = row_idx == 1

            if layout_key == 3 and row_idx == 0:
                continue
            elif layout_key == 3 and row_idx == 1:
                lines.extend(self._sides_with_center(seat_indices, center))
            elif layout_key == 2 and row_idx == 1:
                lines.extend(self._center_only(center))
            elif is_middle and layout_key >= 4:
                real = [i for i in seat_indices if i is not None]
                if len(real) == 1:
                    lines.extend(self._sides_with_center([real[0], None], center))
                elif len(real) >= 2:
                    lines.extend(self._sides_with_center(real[:2], center))
                else:
                    lines.extend(self._center_only(center))
            else:
                real = [i for i in seat_indices if i is not None]
                lines.extend(self._seat_row(real))

        text = Text.from_markup("\n".join(lines))
        return Panel(
            text,
            title="[bold green]♠ ♥ Poker Table ♦ ♣[/bold green]",
            border_style="green",
            height=18,
        )

    def _get_player(self, idx: int) -> dict[str, Any] | None:
        return self._players[idx] if 0 <= idx < len(self._players) else None

    def _seat_row(self, indices: list[int]) -> list[str]:
        boxes = [_make_player_box(self._get_player(i)) for i in indices]
        if not boxes:
            return []

        full_w = BOX_W + 2
        gap = 2
        total = len(boxes) * full_w + (len(boxes) - 1) * gap
        left = max(0, (TABLE_W - total) // 2)

        num_lines = len(boxes[0])
        result = []
        for line_idx in range(num_lines):
            parts = []
            for b_idx, box in enumerate(boxes):
                if b_idx > 0:
                    parts.append(" " * gap)
                parts.append(box[line_idx])
            result.append(" " * left + "".join(parts))
        return result

    def _center_only(self, center: list[str]) -> list[str]:
        return [_pad_center(line, TABLE_W) for line in center]

    def _sides_with_center(self, seat_indices: list[int | None], center: list[str]) -> list[str]:
        left_idx = seat_indices[0] if seat_indices else None
        right_idx = seat_indices[1] if len(seat_indices) > 1 else None

        left_box = _make_player_box(self._get_player(left_idx) if left_idx is not None else None)
        right_box = _make_player_box(self._get_player(right_idx) if right_idx is not None else None)

        max_lines = max(len(left_box), len(center), len(right_box))
        while len(left_box) < max_lines:
            left_box.insert(0, " " * (BOX_W + 2))
        while len(right_box) < max_lines:
            right_box.insert(0, " " * (BOX_W + 2))
        while len(center) < max_lines:
            center.insert(0, " " * (CENTER_W + 2))

        gap = 1
        result = []
        for i in range(max_lines):
            left = left_box[i] if left_idx is not None else " " * (BOX_W + 2)
            right = right_box[i] if right_idx is not None else " " * (BOX_W + 2)
            line = left + " " * gap + center[i] + " " * gap + right
            result.append(line)
        return result
