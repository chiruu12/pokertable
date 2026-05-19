"""Tests for tilt detection system."""

from poker_engine.core.engine import HandSummary, PlayerState, SidePot
from poker_engine.tournament.events import EventBus, TiltEvent, TiltResolvedEvent
from poker_engine.tournament.tilt import (
    STRESSOR_EXISTENTIAL_THREAT,
    STRESSOR_FUTILITY,
    STRESSOR_INVISIBILITY,
    STRESSOR_REPEATED_FAILURE,
    TiltState,
    assess_tilt,
)


def _make_summary(winners: list[str]) -> HandSummary:
    return HandSummary(
        hand_num=1,
        winners=winners,
        pots=[SidePot(100, winners)],
        results=[],
        win_reason="showdown",
    )


def test_existential_threat_triggers():
    player = PlayerState(name="A", chips=200)
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])
    assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_EXISTENTIAL_THREAT in tilt.active_stressors


def test_repeated_failure_escalates():
    player = PlayerState(name="A", chips=800)
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])

    assess_tilt(player, summary, tilt, starting_chips=1000)
    first = tilt.active_stressors[STRESSOR_REPEATED_FAILURE]
    assess_tilt(player, summary, tilt, starting_chips=1000)
    second = tilt.active_stressors[STRESSOR_REPEATED_FAILURE]
    assert second > first


def test_invisibility_after_5_losses():
    player = PlayerState(name="A", chips=800)
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])

    for _ in range(4):
        assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_INVISIBILITY not in tilt.active_stressors

    assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_INVISIBILITY in tilt.active_stressors


def test_futility_on_high_fold_rate():
    player = PlayerState(
        name="A",
        chips=800,
        hands_played=10,
        total_folds=7,
    )
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])
    player.folded = True

    assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_FUTILITY in tilt.active_stressors


def test_tilt_resolves_on_win():
    player = PlayerState(name="A", chips=800)
    tilt = TiltState(
        player_name="A",
        loss_streak=6,
        active_stressors={
            STRESSOR_REPEATED_FAILURE: 0.5,
            STRESSOR_INVISIBILITY: 0.35,
        },
    )
    summary = _make_summary(["A"])

    assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_REPEATED_FAILURE not in tilt.active_stressors
    assert STRESSOR_INVISIBILITY not in tilt.active_stressors
    assert tilt.loss_streak == 0


def test_tilt_events_emitted():
    bus = EventBus()
    events: list = []
    bus.subscribe(events.append)

    player = PlayerState(name="A", chips=200)
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])

    assess_tilt(player, summary, tilt, starting_chips=1000, event_bus=bus)

    tilt_events = [e for e in events if isinstance(e, TiltEvent)]
    assert len(tilt_events) >= 1
    assert any(e.stressor_type == STRESSOR_EXISTENTIAL_THREAT for e in tilt_events)

    # Now win to resolve
    events.clear()
    player.chips = 400
    summary_win = _make_summary(["A"])
    assess_tilt(player, summary_win, tilt, starting_chips=1000, event_bus=bus)

    resolved = [e for e in events if isinstance(e, TiltResolvedEvent)]
    assert len(resolved) >= 1


def test_tilt_no_event_bus():
    player = PlayerState(name="A", chips=200)
    tilt = TiltState(player_name="A")
    summary = _make_summary(["B"])
    assess_tilt(player, summary, tilt, starting_chips=1000, event_bus=None)
    assert STRESSOR_EXISTENTIAL_THREAT in tilt.active_stressors


def test_futility_resolves_when_fold_rate_drops():
    player = PlayerState(
        name="A",
        chips=800,
        hands_played=10,
        total_folds=4,
    )
    tilt = TiltState(
        player_name="A",
        active_stressors={STRESSOR_FUTILITY: 0.3},
    )
    summary = _make_summary(["B"])
    assess_tilt(player, summary, tilt, starting_chips=1000)
    assert STRESSOR_FUTILITY not in tilt.active_stressors
