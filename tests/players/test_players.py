"""Tests for player implementations."""


import pytest

from poker_engine.players.base import BasePlayer
from poker_engine.players.random_player import RandomPlayer
from poker_engine.players.scripted import ScriptedPlayer

SAMPLE_ACTIONS = [
    {"action": "fold"},
    {"action": "call", "amount": 20},
    {"action": "raise", "amount": 40},
]


class TestRandomPlayer:
    def test_satisfies_protocol(self):
        player = RandomPlayer("Bot1")
        assert isinstance(player, BasePlayer)

    def test_name_property(self):
        player = RandomPlayer("TestBot")
        assert player.name == "TestBot"

    @pytest.mark.asyncio
    async def test_always_returns_valid_action(self):
        player = RandomPlayer("Bot1", seed=42)
        for _ in range(50):
            result = await player.decide({}, SAMPLE_ACTIONS)
            assert result in SAMPLE_ACTIONS

    @pytest.mark.asyncio
    async def test_deterministic_with_seed(self):
        p1 = RandomPlayer("A", seed=99)
        p2 = RandomPlayer("B", seed=99)
        results1 = [await p1.decide({}, SAMPLE_ACTIONS) for _ in range(20)]
        results2 = [await p2.decide({}, SAMPLE_ACTIONS) for _ in range(20)]
        assert results1 == results2

    @pytest.mark.asyncio
    async def test_handles_single_action(self):
        player = RandomPlayer("Bot1", seed=1)
        result = await player.decide({}, [{"action": "check"}])
        assert result == {"action": "check"}

    @pytest.mark.asyncio
    async def test_observe_does_nothing(self):
        player = RandomPlayer("Bot1")
        await player.observe({"type": "test"})

    @pytest.mark.asyncio
    async def test_commentary_is_none(self):
        player = RandomPlayer("Bot1")
        assert await player.get_commentary() is None


class TestScriptedPlayer:
    def test_satisfies_protocol(self):
        player = ScriptedPlayer("Script1", [{"action": "fold"}])
        assert isinstance(player, BasePlayer)

    @pytest.mark.asyncio
    async def test_follows_script(self):
        script = [
            {"action": "call"},
            {"action": "raise", "amount": 40},
            {"action": "fold"},
        ]
        player = ScriptedPlayer("Script1", script)
        r1 = await player.decide({}, SAMPLE_ACTIONS)
        r2 = await player.decide({}, SAMPLE_ACTIONS)
        r3 = await player.decide({}, SAMPLE_ACTIONS)
        assert r1 == {"action": "call"}
        assert r2 == {"action": "raise", "amount": 40}
        assert r3 == {"action": "fold"}

    @pytest.mark.asyncio
    async def test_loops_when_exhausted(self):
        script = [{"action": "call"}, {"action": "fold"}]
        player = ScriptedPlayer("Script1", script)
        results = [await player.decide({}, SAMPLE_ACTIONS) for _ in range(4)]
        assert results == [
            {"action": "call"},
            {"action": "fold"},
            {"action": "call"},
            {"action": "fold"},
        ]

    @pytest.mark.asyncio
    async def test_empty_script_uses_first_valid(self):
        player = ScriptedPlayer("Script1", [])
        result = await player.decide({}, SAMPLE_ACTIONS)
        assert result == SAMPLE_ACTIONS[0]

    @pytest.mark.asyncio
    async def test_observe_records_events(self):
        player = ScriptedPlayer("Script1", [])
        await player.observe({"type": "deal"})
        await player.observe({"type": "action"})
        assert len(player._events) == 2
