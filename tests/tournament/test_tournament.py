"""Tests for tournament components."""

import pytest

from poker_engine.players.random_player import RandomPlayer
from poker_engine.players.scripted import ScriptedPlayer
from poker_engine.tournament.blind_schedule import BlindLevel, BlindSchedule
from poker_engine.tournament.director import TournamentDirector
from poker_engine.tournament.events import EventBus, HandStartEvent, TournamentEvent
from poker_engine.tournament.history import HandHistory, HandRecord
from poker_engine.tournament.payout import PayoutStructure


class TestBlindSchedule:
    def test_turbo_has_levels(self):
        schedule = BlindSchedule.turbo()
        assert len(schedule.levels) == 8
        assert schedule.levels[0].small_blind == 10

    def test_standard_has_levels(self):
        schedule = BlindSchedule.standard()
        assert len(schedule.levels) == 8
        assert schedule.levels[0].duration_hands == 10

    def test_current_level_first(self):
        schedule = BlindSchedule.turbo()
        level = schedule.current_level(0)
        assert level.level == 1
        assert level.small_blind == 10

    def test_current_level_advances(self):
        schedule = BlindSchedule.turbo()
        level = schedule.current_level(5)
        assert level.level == 2

    def test_current_level_caps_at_last(self):
        schedule = BlindSchedule.turbo()
        level = schedule.current_level(999)
        assert level.level == 8

    def test_empty_schedule_raises(self):
        with pytest.raises(ValueError):
            BlindSchedule([])


class TestPayoutStructure:
    def test_winner_take_all(self):
        payout = PayoutStructure.winner_take_all()
        assert payout.calculate(1000) == [1000]

    def test_top_2(self):
        payout = PayoutStructure.top_2()
        amounts = payout.calculate(1000)
        assert len(amounts) == 2
        assert sum(amounts) == 1000

    def test_top_3(self):
        payout = PayoutStructure.top_3()
        amounts = payout.calculate(1000)
        assert len(amounts) == 3
        assert sum(amounts) == 1000

    def test_default_for_2_players(self):
        payout = PayoutStructure.default(2)
        assert payout.name == "Winner Take All"

    def test_default_for_6_players(self):
        payout = PayoutStructure.default(6)
        assert payout.name == "Top 3"


class TestEventBus:
    def test_subscribe_and_emit(self):
        bus = EventBus()
        received = []
        bus.subscribe(lambda e: received.append(e))
        bus.emit(HandStartEvent(hand_num=1, dealer="Alice"))
        assert len(received) == 1
        assert received[0].event_type == "hand_start"

    def test_history_tracked(self):
        bus = EventBus()
        bus.emit(TournamentEvent(event_type="test"))
        bus.emit(TournamentEvent(event_type="test2"))
        assert len(bus.get_history()) == 2

    def test_clear_history(self):
        bus = EventBus()
        bus.emit(TournamentEvent(event_type="test"))
        bus.clear()
        assert len(bus.get_history()) == 0


class TestHandHistory:
    def test_record_and_export(self, tmp_path):
        history = HandHistory()
        record = HandRecord(
            hand_num=1,
            players=[{"name": "A", "chips": 1000}],
            blinds=(10, 20, 0),
            winners=["A"],
            win_reason="showdown",
        )
        history.record(record)
        assert len(history.hands) == 1

        path = tmp_path / "history.json"
        history.to_file(path)
        loaded = HandHistory.from_file(path)
        assert len(loaded.hands) == 1
        assert loaded.hands[0].hand_num == 1


class TestTournamentDirector:
    @pytest.mark.asyncio
    async def test_full_tournament_with_random_players(self):
        players = [
            RandomPlayer("Alice", seed=1),
            RandomPlayer("Bob", seed=2),
            RandomPlayer("Charlie", seed=3),
        ]
        schedule = BlindSchedule.turbo()
        director = TournamentDirector(
            players, schedule, starting_chips=200, seed=42, max_hands=30,
        )

        events_received = []
        director.on_event(lambda e: events_received.append(e))

        result = await director.run()

        assert result.hands_played > 0
        assert len(result.standings) == 3
        total_chips = sum(s["chips"] for s in result.standings)
        assert total_chips == 200 * 3
        assert len(events_received) > 0

    @pytest.mark.asyncio
    async def test_scripted_tournament(self):
        players = [
            ScriptedPlayer("A", [{"action": "call"}]),
            ScriptedPlayer("B", [{"action": "call"}]),
        ]
        schedule = BlindSchedule([BlindLevel(1, 10, 20, 0, 5)])
        director = TournamentDirector(
            players, schedule, starting_chips=100, seed=1, max_hands=10,
        )

        result = await director.run()
        assert result.hands_played > 0
        total = sum(s["chips"] for s in result.standings)
        assert total == 200

    @pytest.mark.asyncio
    async def test_history_recorded(self):
        players = [
            RandomPlayer("A", seed=1),
            RandomPlayer("B", seed=2),
        ]
        schedule = BlindSchedule.turbo()
        director = TournamentDirector(
            players, schedule, starting_chips=100, seed=42, max_hands=5,
        )
        await director.run()
        assert len(director.history.hands) > 0
