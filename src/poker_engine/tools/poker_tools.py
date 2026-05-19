"""Poker tools for LLM agent interaction. Each player gets a scoped toolkit."""

from __future__ import annotations

from typing import Any

from poker_engine.core.cards import describe_hand, evaluate_hand
from poker_engine.core.engine import ActionType, PokerEngine
from poker_engine.core.equity import calculate_equity
from poker_engine.tools.decorator import ToolDef, tool
from poker_engine.tools.registry import ToolRegistry


class PokerToolkit:
    """Tools for one player to interact with a poker game.

    Each LLM agent gets its own PokerToolkit instance scoped to its player.
    Enforces information hiding — agents can only see their own hole cards.
    """

    def __init__(self, engine: PokerEngine, player_name: str) -> None:
        self._engine = engine
        self._player_name = player_name
        self._registry = ToolRegistry()
        self._registry.register_all(
            self.view_hand,
            self.view_table,
            self.check_equity,
            self.view_opponents,
            self.place_action,
        )

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def get_tools(self) -> list[ToolDef]:
        return self._registry.list_tools()

    def _get_position(self) -> str:
        try:
            sb, bb = self._engine.get_sb_bb()
            dealer = self._engine.get_dealer()
            if self._player_name == dealer.name:
                return "BTN"
            if self._player_name == sb.name:
                return "SB"
            if self._player_name == bb.name:
                return "BB"
        except (IndexError, ValueError):
            pass
        return ""

    @tool()
    def view_hand(self) -> dict[str, Any]:
        """View your hole cards and current hand strength.

        Returns your two private cards, the current best hand evaluation
        if community cards are on the board, and your chip count.
        """
        player = self._engine._get_player(self._player_name)
        cards_str = [str(c) for c in player.hole_cards]
        result: dict[str, Any] = {
            "hole_cards": cards_str,
            "chips": player.chips,
            "bet_this_round": player.bet_this_round,
            "position": self._get_position(),
        }
        if self._engine.community:
            hand = evaluate_hand(player.hole_cards + self._engine.community)
            result["current_hand"] = describe_hand(hand)
            result["hand_rank"] = hand.rank.name
        return result

    @tool()
    def view_table(self) -> dict[str, Any]:
        """View the community cards, pot size, current bet, and game phase.

        Shows all public information about the current state of the hand.
        """
        current = self._engine.get_current_player()
        return {
            "community_cards": [str(c) for c in self._engine.community],
            "pot": self._engine.pot,
            "current_bet": self._engine.current_bet,
            "phase": self._engine.phase.name,
            "hand_number": self._engine.hand_num,
            "players_in_hand": len([p for p in self._engine.players if not p.folded]),
            "your_turn": current is not None and current.name == self._player_name,
        }

    @tool()
    def check_equity(self, num_simulations: int = 500) -> dict[str, Any]:
        """Calculate your win probability using Monte Carlo simulation.

        Args:
            num_simulations: Simulations to run (100-2000). More = slower but accurate.
        """
        num_simulations = max(100, min(2000, num_simulations))
        player = self._engine._get_player(self._player_name)
        active_opponents = len(
            [p for p in self._engine.players if not p.folded and p.name != self._player_name]
        )
        eq = calculate_equity(
            player.hole_cards,
            self._engine.community,
            num_opponents=active_opponents,
            num_simulations=num_simulations,
        )
        return {
            "current_hand": eq.current_hand,
            "win_probability": eq.win_probability,
            "tie_probability": eq.tie_probability,
            "hand_improvement": eq.hand_improvement,
        }

    @tool()
    def view_opponents(self) -> list[dict[str, Any]]:
        """View public information about all opponents.

        Shows chip counts, position, whether they've folded or gone all-in,
        and historical stats (fold rate, raise rate) for each opponent.
        """
        opponents = []
        for p in self._engine.players:
            if p.name == self._player_name:
                continue
            info: dict[str, Any] = {
                "name": p.name,
                "chips": p.chips,
                "folded": p.folded,
                "all_in": p.all_in,
                "bet_this_round": p.bet_this_round,
            }
            if p.hands_played > 0:
                info["stats"] = {
                    "hands_played": p.hands_played,
                    "fold_rate": round(p.total_folds / p.hands_played, 2),
                    "raise_rate": round(p.total_raises / p.hands_played, 2),
                }
            if p.name in self._engine.showed_cards:
                info["shown_cards"] = [str(c) for c in self._engine.showed_cards[p.name]]
            opponents.append(info)
        return opponents

    @tool()
    def place_action(self, action: str, amount: int = 0) -> dict[str, Any]:
        """Place your poker action.

        Args:
            action: One of: "fold", "check", "call", "raise", "all_in".
            amount: For "raise" — the total bet to raise TO. Ignored for others.
        """
        current = self._engine.get_current_player()
        if current is None or current.name != self._player_name:
            return {"error": "It is not your turn."}

        action_map = {
            "fold": ActionType.FOLD,
            "check": ActionType.CHECK,
            "call": ActionType.CALL,
            "raise": ActionType.RAISE,
            "all_in": ActionType.ALL_IN,
        }

        action_type = action_map.get(action.lower())
        if action_type is None:
            return {"error": f"Invalid action: {action}. Use: fold, check, call, raise, all_in"}

        valid = self._engine.get_valid_actions(self._player_name)
        chosen = self._find_matching_action(valid, action_type, amount)
        if chosen is None:
            valid_strs = [
                f"{a.type.name.lower()}({a.amount})"
                for a in valid
                if a.type != ActionType.SHOW_CARDS
            ]
            return {"error": f"Action not valid. Valid actions: {valid_strs}"}

        result = self._engine.apply_action(self._player_name, chosen)
        return {
            "action": action,
            "chips_spent": result.chips_spent,
            "your_chips": result.new_chip_count,
            "pot": result.pot_after,
        }

    def _find_matching_action(
        self, valid: list[Any], action_type: ActionType, amount: int
    ) -> Any | None:
        from poker_engine.core.engine import Action

        if action_type == ActionType.RAISE:
            raises = [a for a in valid if a.type == ActionType.RAISE]
            if not raises:
                return None
            if amount > 0:
                closest = min(raises, key=lambda a: abs(a.amount - amount))
                if amount >= raises[0].amount:
                    return Action(ActionType.RAISE, max(amount, raises[0].amount))
                return closest
            return raises[0]

        for a in valid:
            if a.type == action_type:
                return a
        return None
