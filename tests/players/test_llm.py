"""Tests for LLMPlayer — LLM-driven poker player via tool-calling."""

from __future__ import annotations

from typing import Any

import pytest

from poker_engine.core.engine import PokerEngine
from poker_engine.players.base import BasePlayer
from poker_engine.players.llm import DEFAULT_SYSTEM_PROMPT, LLMPlayer
from poker_engine.tools.decorator import ToolDef
from poker_engine.tools.poker_tools import PokerToolkit

# ── Mock adapter ─────────────────────────────────────────────────────


class MockLLMAdapter:
    """Mock that returns scripted responses for testing LLMPlayer."""

    def __init__(self, responses: list[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self._call_count = 0
        self.calls: list[dict[str, Any]] = []

    async def generate(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.7,
    ) -> dict[str, Any]:
        self.calls.append({"messages": messages, "tools": tools})
        response = self._responses[self._call_count % len(self._responses)]
        self._call_count += 1
        return response


# ── Helpers ──────────────────────────────────────────────────────────


def _bind_toolkit_registry(tk: PokerToolkit) -> None:
    """Fix ToolDef.fn entries so they reference the bound methods.

    The @tool() decorator stores the unbound class function in ToolDef.fn,
    so registry.call() fails with a missing 'self' argument.  This helper
    replaces each ToolDef with one whose .fn is the bound method.
    """
    bound_map = {
        "view_hand": tk.view_hand,
        "view_table": tk.view_table,
        "check_equity": tk.check_equity,
        "view_opponents": tk.view_opponents,
        "place_action": tk.place_action,
    }
    for name, bound_method in bound_map.items():
        old = tk.registry.get(name)
        if old is not None:
            tk.registry._tools[name] = ToolDef(
                name=old.name,
                description=old.description,
                parameters=old.parameters,
                fn=bound_method,
            )


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def game():
    """Start a 2-player game so the first player to act is deterministic."""
    engine = PokerEngine(["TestLLM", "Opponent"], seed=42)
    engine.new_hand()
    return engine


@pytest.fixture
def toolkit(game):
    return PokerToolkit(game, "TestLLM")


def _current_player_name(game: PokerEngine) -> str:
    p = game.get_current_player()
    assert p is not None
    return p.name


def _make_player(
    game: PokerEngine,
    toolkit: PokerToolkit,
    responses: list[dict[str, Any]],
    **kwargs: Any,
) -> tuple[LLMPlayer, MockLLMAdapter]:
    adapter = MockLLMAdapter(responses)
    player = LLMPlayer(
        name="TestLLM",
        adapter=adapter,
        toolkit=toolkit,
        **kwargs,
    )
    return player, adapter


# ── Protocol conformance ─────────────────────────────────────────────


def test_llm_player_satisfies_base_player(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    assert isinstance(player, BasePlayer)


def test_llm_player_name(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    assert player.name == "TestLLM"


# ── decide: tool_calls flow ─────────────────────────────────────────


async def test_decide_view_hand_then_place_action(game, toolkit):
    """LLM calls view_hand, then place_action — returns the action."""
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    _bind_toolkit_registry(tk)
    responses = [
        {
            "content": "Let me check my cards",
            "tool_calls": [
                {"id": "tc-1", "name": "view_hand", "arguments": {}},
            ],
        },
        {
            "content": "I'll call",
            "tool_calls": [
                {
                    "id": "tc-2",
                    "name": "place_action",
                    "arguments": {"action": "call"},
                },
            ],
        },
    ]
    player, adapter = _make_player(game, tk, responses)
    player._name = current_name

    valid = [{"action": "fold"}, {"action": "call", "amount": 20}]
    result = await player.decide({}, valid)
    assert result["action"] == "call"
    assert adapter._call_count == 2


async def test_decide_direct_place_action(game, toolkit):
    """LLM immediately calls place_action on first response."""
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    _bind_toolkit_registry(tk)
    responses = [
        {
            "content": "Fold right away",
            "tool_calls": [
                {
                    "id": "tc-1",
                    "name": "place_action",
                    "arguments": {"action": "fold"},
                },
            ],
        },
    ]
    player, adapter = _make_player(game, tk, responses)
    player._name = current_name

    result = await player.decide({}, [{"action": "fold"}])
    assert result["action"] == "fold"
    assert adapter._call_count == 1


# ── decide: no tool_calls → fallback ────────────────────────────────


async def test_decide_no_tool_calls_falls_back(game, toolkit):
    """When LLM returns text only, player falls back to check/call."""
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    responses = [{"content": "I'm confused", "tool_calls": None}]
    player, _ = _make_player(game, tk, responses)
    player._name = current_name

    valid = [{"action": "fold"}, {"action": "call", "amount": 20}]
    result = await player.decide({"phase": "PRE_FLOP", "pot": 30}, valid)
    assert result["action"] == "call"


async def test_decide_empty_tool_calls_falls_back(game, toolkit):
    """Empty tool_calls list also triggers fallback."""
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    responses = [{"content": "hmm", "tool_calls": []}]
    player, _ = _make_player(game, tk, responses)
    player._name = current_name

    valid = [{"action": "fold"}, {"action": "check"}]
    result = await player.decide({}, valid)
    assert result["action"] == "check"


# ── decide: exhausts max_tool_rounds → fold ──────────────────────────


async def test_decide_exhausts_rounds_returns_fold(game, toolkit):
    """When max_tool_rounds exceeded without place_action → fold."""
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    _bind_toolkit_registry(tk)
    # Always call view_hand — never calls place_action
    responses = [
        {
            "content": "Checking again",
            "tool_calls": [
                {"id": "tc-x", "name": "view_hand", "arguments": {}},
            ],
        },
    ]
    player, adapter = _make_player(game, tk, responses, max_tool_rounds=3)
    player._name = current_name

    result = await player.decide({}, [{"action": "fold"}])
    assert result == {"action": "fold"}
    assert adapter._call_count == 3


# ── observe ──────────────────────────────────────────────────────────


async def test_observe_adds_event(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    await player.observe({"type": "deal", "cards": ["Ah", "Kd"]})
    assert len(player._conversation) == 1
    assert "[Game event]" in player._conversation[0]["content"]


async def test_observe_multiple_events(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    await player.observe({"type": "deal"})
    await player.observe({"type": "bet", "amount": 100})
    assert len(player._conversation) == 2


# ── get_commentary ───────────────────────────────────────────────────


async def test_get_commentary_returns_last_text(game, toolkit):
    current_name = _current_player_name(game)
    tk = PokerToolkit(game, current_name)
    _bind_toolkit_registry(tk)
    responses = [
        {
            "content": "Great hand!",
            "tool_calls": [
                {
                    "id": "tc-1",
                    "name": "place_action",
                    "arguments": {"action": "fold"},
                },
            ],
        },
    ]
    player, _ = _make_player(game, tk, responses)
    player._name = current_name

    await player.decide({}, [{"action": "fold"}])
    commentary = await player.get_commentary()
    assert commentary == "Great hand!"


async def test_get_commentary_none_initially(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    assert await player.get_commentary() is None


# ── _fallback_action ─────────────────────────────────────────────────


def test_fallback_prefers_check(game, toolkit):
    valid = [{"action": "fold"}, {"action": "check"}]
    result = LLMPlayer._fallback_action(valid)
    assert result["action"] == "check"


def test_fallback_prefers_call(game, toolkit):
    valid = [{"action": "fold"}, {"action": "call", "amount": 20}]
    result = LLMPlayer._fallback_action(valid)
    assert result["action"] == "call"


def test_fallback_returns_first_when_no_check_call():
    valid = [{"action": "raise", "amount": 40}]
    result = LLMPlayer._fallback_action(valid)
    assert result["action"] == "raise"


def test_fallback_empty_returns_fold():
    result = LLMPlayer._fallback_action([])
    assert result == {"action": "fold"}


# ── system_prompt / personality ──────────────────────────────────────


def test_custom_system_prompt(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(
        name="TestLLM",
        adapter=adapter,
        toolkit=toolkit,
        system_prompt="Custom prompt",
    )
    assert player._system_prompt == "Custom prompt"


def test_personality_appended(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(
        name="TestLLM",
        adapter=adapter,
        toolkit=toolkit,
        personality="Aggressive bluffer",
    )
    assert "Aggressive bluffer" in player._system_prompt
    assert DEFAULT_SYSTEM_PROMPT in player._system_prompt


def test_default_prompt_when_no_overrides(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    assert player._system_prompt == DEFAULT_SYSTEM_PROMPT


# ── _build_turn_prompt ───────────────────────────────────────────────


def test_build_turn_prompt_content(game, toolkit):
    adapter = MockLLMAdapter([])
    player = LLMPlayer(name="TestLLM", adapter=adapter, toolkit=toolkit)
    prompt = player._build_turn_prompt(
        {"phase": "FLOP", "pot": 200},
        [{"action": "check"}, {"action": "raise", "amount": 40}],
    )
    assert "FLOP" in prompt
    assert "200" in prompt
    assert "check" in prompt
    assert "raise(40)" in prompt
