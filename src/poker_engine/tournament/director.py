"""Tournament director — orchestrates the full tournament lifecycle."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from poker_engine.core.engine import ActionType, Phase, PokerEngine
from poker_engine.tools.poker_tools import PokerToolkit
from poker_engine.tournament.blind_schedule import BlindSchedule
from poker_engine.tournament.events import (
    ActionEvent,
    BlindLevelEvent,
    CardsDealtEvent,
    CommentaryEvent,
    EliminationEvent,
    EventBus,
    HandEndEvent,
    HandStartEvent,
    PhaseChangeEvent,
    ShowdownEvent,
    TableTalkEvent,
)
from poker_engine.tournament.history import HandHistory, HandRecord
from poker_engine.tournament.payout import PayoutStructure
from poker_engine.tournament.table_manager import TableManager


@dataclass
class TournamentResult:
    standings: list[dict[str, Any]] = field(default_factory=list)
    hands_played: int = 0
    payouts: list[dict[str, Any]] = field(default_factory=list)


class HandOrchestrator:
    """Plays a single hand, soliciting decisions from players via tools."""

    def __init__(
        self,
        engine: PokerEngine,
        players: dict[str, Any],
        event_bus: EventBus,
        table_talk: bool = True,
        phase_delay: float = 0.0,
        action_delay: float = 0.0,
    ) -> None:
        self._engine = engine
        self._players = players
        self._event_bus = event_bus
        self._table_talk = table_talk
        self._phase_delay = phase_delay
        self._action_delay = action_delay
        self._toolkits: dict[str, PokerToolkit] = {
            name: PokerToolkit(engine, name, table_talk=table_talk) for name in players
        }

    async def _yield(self, delay: float = 0.0) -> None:
        """Yield to event loop so TUI can render. Uses action_delay if set."""
        t = delay or self._action_delay
        if t > 0:
            await asyncio.sleep(t)
        else:
            await asyncio.sleep(0)

    async def play_hand(self) -> Any:
        engine = self._engine
        engine.new_hand()

        dealer = engine.get_dealer()
        self._event_bus.emit(
            HandStartEvent(
                hand_num=engine.hand_num,
                dealer=dealer.name,
            )
        )

        hands = {p.name: [str(c) for c in p.hole_cards] for p in engine.players if not p.folded}
        self._event_bus.emit(CardsDealtEvent(hands=hands))
        await self._yield()

        for name, player in self._players.items():
            await player.observe({"type": "new_hand", "hand_num": engine.hand_num})

        while not engine.is_hand_over():
            if engine.is_betting_round_complete():
                active = [p for p in engine.players if not p.folded]
                if len(active) <= 1:
                    break
                if engine.phase == Phase.RIVER:
                    break
                if engine.phase == Phase.SHOWDOWN:
                    break
                engine.advance_phase()
                self._event_bus.emit(
                    PhaseChangeEvent(
                        phase=engine.phase.name,
                        community=[str(c) for c in engine.community],
                    )
                )
                if self._phase_delay > 0:
                    await asyncio.sleep(self._phase_delay)
                continue

            current = engine.get_current_player()
            if current is None:
                break

            player = self._players.get(current.name)
            if player is None:
                break

            game_state = self._build_game_state(current.name)
            valid_actions = self._build_valid_actions(current.name)

            try:
                decision = await player.decide(game_state, valid_actions)
            except Exception:
                decision = {"action": "fold"}

            action_str = decision.get("action", "fold")
            amount = decision.get("amount", 0)
            toolkit = self._toolkits[current.name]
            result = toolkit.place_action(action=action_str, amount=amount)

            if "error" in result:
                for a in valid_actions:
                    if a["action"] in ("check", "call"):
                        toolkit.place_action(action=a["action"])
                        action_str = a["action"]
                        amount = a.get("amount", 0)
                        break
                else:
                    toolkit.place_action(action="fold")
                    action_str = "fold"
                    amount = 0

            self._event_bus.emit(
                ActionEvent(
                    player=current.name,
                    action=action_str,
                    amount=amount,
                    pot=engine.pot,
                )
            )

            for name, p in self._players.items():
                if name != current.name:
                    await p.observe(
                        {
                            "type": "player_action",
                            "player": current.name,
                            "action": action_str,
                            "amount": amount,
                        }
                    )

            commentary = await player.get_commentary()
            if commentary:
                self._event_bus.emit(
                    CommentaryEvent(
                        player=current.name,
                        text=commentary,
                    )
                )

            if self._table_talk and hasattr(player, "get_table_talk"):
                try:
                    game_state = self._build_game_state(current.name)
                    talk = await player.get_table_talk(game_state)
                    if talk:
                        self._event_bus.emit(TableTalkEvent(player=current.name, message=talk))
                        for name, p in self._players.items():
                            if name != current.name:
                                await p.observe(
                                    {
                                        "type": "table_talk",
                                        "player": current.name,
                                        "message": talk,
                                    }
                                )
                except Exception:
                    pass

            await self._yield()

        active = [p for p in engine.players if not p.folded]
        if len(active) <= 1:
            summary = engine.resolve_fold_win()
        else:
            summary = engine.resolve_showdown()
            if summary.results:
                showdown_results = [
                    {
                        "player": r.player_name,
                        "hand": r.hand_description,
                        "cards": [str(c) for c in r.hole_cards],
                        "winnings": r.winnings,
                    }
                    for r in summary.results
                ]
                self._event_bus.emit(ShowdownEvent(results=showdown_results))

        self._event_bus.emit(
            HandEndEvent(
                hand_num=summary.hand_num,
                winners=summary.winners,
                win_reason=summary.win_reason,
            )
        )
        await self._yield()
        engine.rotate_dealer()

        return summary

    def _build_game_state(self, player_name: str) -> dict[str, Any]:
        engine = self._engine
        player = engine._get_player(player_name)
        return {
            "phase": engine.phase.name,
            "pot": engine.pot,
            "current_bet": engine.current_bet,
            "community_cards": [str(c) for c in engine.community],
            "hole_cards": [str(c) for c in player.hole_cards],
            "your_chips": player.chips,
            "players_in_hand": len([p for p in engine.players if not p.folded]),
        }

    def _build_valid_actions(self, player_name: str) -> list[dict[str, Any]]:
        actions = []
        for a in self._engine.get_valid_actions(player_name):
            if a.type == ActionType.SHOW_CARDS:
                continue
            entry: dict[str, Any] = {"action": a.type.name.lower()}
            if a.amount:
                entry["amount"] = a.amount
            actions.append(entry)
        return actions


class TournamentDirector:
    """Top-level orchestrator for a poker tournament."""

    def __init__(
        self,
        players: list[Any],
        blind_schedule: BlindSchedule,
        starting_chips: int = 1000,
        payout: PayoutStructure | None = None,
        seed: int | None = None,
        hand_delay: float = 0.0,
        phase_delay: float = 0.0,
        action_delay: float = 0.0,
        max_hands: int = 500,
        table_talk: bool = True,
    ) -> None:
        self._players = players
        self._blind_schedule = blind_schedule
        self._starting_chips = starting_chips
        self._payout = payout or PayoutStructure.default(len(players))
        self._seed = seed
        self._hand_delay = hand_delay
        self._phase_delay = phase_delay
        self._action_delay = action_delay
        self._max_hands = max_hands
        self._table_talk = table_talk
        self._event_bus = EventBus()
        self._history = HandHistory()
        self._table_manager = TableManager(max_per_table=9)
        self._running = False
        self._hands_played = 0
        self._last_blind_level = 0

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def history(self) -> HandHistory:
        return self._history

    @property
    def hands_played(self) -> int:
        return self._hands_played

    @property
    def tables(self) -> list[Any]:
        return self._table_manager.tables

    def on_event(self, callback: Any) -> None:
        self._event_bus.subscribe(callback)

    async def run(self) -> TournamentResult:
        self._running = True
        self._last_blind_level = 0
        self._hands_played = 0
        self._table_manager.seat_players(
            self._players,
            self._starting_chips,
            self._seed,
        )

        while self._running and self._hands_played < self._max_hands:
            active_tables = self._table_manager.active_tables()
            if not active_tables:
                break

            blind = self._blind_schedule.current_level(self._hands_played)
            if blind.level != self._last_blind_level:
                self._last_blind_level = blind.level
                self._event_bus.emit(
                    BlindLevelEvent(
                        level=blind.level,
                        small_blind=blind.small_blind,
                        big_blind=blind.big_blind,
                        ante=blind.ante,
                    )
                )

            for table in active_tables:
                table.engine._small_blind = blind.small_blind
                table.engine._big_blind = blind.big_blind

                orch = HandOrchestrator(
                    table.engine,
                    table.players,
                    self._event_bus,
                    table_talk=self._table_talk,
                    phase_delay=self._phase_delay,
                    action_delay=self._action_delay,
                )
                summary = await orch.play_hand()

                if summary:
                    chips = {p.name: p.chips for p in table.engine.players}
                    record = HandRecord.from_summary(
                        summary,
                        chips,
                        (blind.small_blind, blind.big_blind, blind.ante),
                    )
                    self._history.record(record)

                self._hands_played += 1

            eliminated = self._table_manager.eliminate_busted()
            for name in eliminated:
                position = len(self._players) - len(self._table_manager.eliminated) + 1
                self._event_bus.emit(
                    EliminationEvent(
                        player=name,
                        position=position,
                    )
                )

            self._table_manager.rebalance()

            if self._hand_delay > 0:
                await asyncio.sleep(self._hand_delay)

        return self._compute_results()

    def stop(self) -> None:
        self._running = False

    def _compute_results(self) -> TournamentResult:
        if not self._table_manager.tables:
            return TournamentResult(hands_played=self._hands_played)

        all_players = []
        for table in self._table_manager.tables:
            for p in table.engine.players:
                all_players.append(
                    {
                        "name": p.name,
                        "chips": p.chips,
                        "hands_played": p.hands_played,
                        "hands_won": p.hands_won,
                    }
                )

        all_players.sort(key=lambda x: x["chips"], reverse=True)

        prize_pool = self._starting_chips * len(self._players)
        payout_amounts = self._payout.calculate(prize_pool)
        payouts = []
        for i, amount in enumerate(payout_amounts):
            if i < len(all_players):
                payouts.append({"place": i + 1, "player": all_players[i]["name"], "amount": amount})

        return TournamentResult(
            standings=all_players,
            hands_played=self._hands_played,
            payouts=payouts,
        )
