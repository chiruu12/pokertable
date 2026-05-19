"""Shared helpers for integration test scripts."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from poker_engine.core.engine import ActionType, Phase, PokerEngine  # noqa: E402
from poker_engine.players.random_player import RandomPlayer  # noqa: E402
from poker_engine.tools.poker_tools import PokerToolkit  # noqa: E402


async def run_hand(
    engine: PokerEngine,
    players: dict[str, Any],
    hand_num: int,
) -> None:
    """Play one hand to completion, printing actions."""
    engine.new_hand()
    print(f"\n{'='*50}")
    print(f"Hand #{hand_num}")
    print(f"{'='*50}")

    for p in engine.players:
        if not p.folded:
            print(f"  {p.name}: {p.chips} chips")

    while not engine.is_hand_over():
        if engine.is_betting_round_complete():
            active = [p for p in engine.players if not p.folded]
            if len(active) <= 1 or engine.phase == Phase.RIVER:
                break
            if engine.phase == Phase.SHOWDOWN:
                break
            engine.advance_phase()
            cards = " ".join(str(c) for c in engine.community)
            print(f"\n  [{engine.phase.name}] Community: {cards}")
            continue

        current = engine.get_current_player()
        if current is None:
            break

        player = players.get(current.name)
        if player is None:
            break

        game_state = {
            "phase": engine.phase.name,
            "pot": engine.pot,
            "current_bet": engine.current_bet,
            "community_cards": [str(c) for c in engine.community],
            "hole_cards": [str(c) for c in current.hole_cards],
            "your_chips": current.chips,
        }

        valid = engine.get_valid_actions(current.name)
        valid_dicts = []
        for a in valid:
            if a.type == ActionType.SHOW_CARDS:
                continue
            entry: dict[str, Any] = {"action": a.type.name.lower()}
            if a.amount:
                entry["amount"] = a.amount
            valid_dicts.append(entry)

        decision = await player.decide(game_state, valid_dicts)
        action_str = decision.get("action", "fold")
        amount = decision.get("amount", 0)

        toolkit = PokerToolkit(engine, current.name)
        result = toolkit.place_action(action=action_str, amount=amount)

        if "error" in result:
            for a in valid_dicts:
                if a["action"] in ("check", "call"):
                    toolkit.place_action(action=a["action"])
                    action_str = a["action"]
                    break
            else:
                toolkit.place_action(action="fold")
                action_str = "fold"

        suffix = f" ({amount})" if amount and action_str == "raise" else ""
        print(f"  {current.name}: {action_str}{suffix}")

        commentary = await player.get_commentary()
        if commentary:
            short = commentary[:80] + "..." if len(commentary) > 80 else commentary
            print(f"    thought: {short}")

    active = [p for p in engine.players if not p.folded]
    if len(active) <= 1:
        summary = engine.resolve_fold_win()
    else:
        summary = engine.resolve_showdown()

    print(f"\n  Winner(s): {', '.join(summary.winners)} ({summary.win_reason})")
    engine.rotate_dealer()


def print_final_standings(engine: PokerEngine) -> None:
    """Print final chip counts."""
    print(f"\n{'='*50}")
    print("FINAL STANDINGS")
    print(f"{'='*50}")
    standings = sorted(engine.players, key=lambda p: p.chips, reverse=True)
    for i, p in enumerate(standings, 1):
        print(f"  {i}. {p.name}: {p.chips} chips")
