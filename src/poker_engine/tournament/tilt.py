"""Tilt detection — engine-native stressor assessment (no Hive dependency)."""

from __future__ import annotations

from dataclasses import dataclass, field

from poker_engine.core.engine import HandSummary, PlayerState
from poker_engine.tournament.events import EventBus, TiltEvent, TiltResolvedEvent

STRESSOR_EXISTENTIAL_THREAT = "existential_threat"
STRESSOR_REPEATED_FAILURE = "repeated_failure"
STRESSOR_INVISIBILITY = "invisibility"
STRESSOR_FUTILITY = "futility"


@dataclass
class TiltState:
    """Tracks tilt stressors for a single player."""

    player_name: str
    loss_streak: int = 0
    active_stressors: dict[str, float] = field(default_factory=dict)

    @property
    def total_severity(self) -> float:
        if not self.active_stressors:
            return 0.0
        return sum(self.active_stressors.values()) / len(self.active_stressors)


def assess_tilt(
    player: PlayerState,
    summary: HandSummary,
    tilt: TiltState,
    starting_chips: int,
    event_bus: EventBus | None = None,
) -> TiltState:
    """Assess and update tilt state after a hand. Emits events if bus provided."""
    won = player.name in summary.winners

    if won:
        tilt.loss_streak = 0
        for stype in [STRESSOR_REPEATED_FAILURE, STRESSOR_INVISIBILITY]:
            if stype in tilt.active_stressors:
                del tilt.active_stressors[stype]
                if event_bus:
                    event_bus.emit(
                        TiltResolvedEvent(
                            player=player.name,
                            stressor_type=stype,
                            reason="Won a hand",
                        )
                    )
    else:
        tilt.loss_streak += 1

        if player.chips < starting_chips * 0.3:
            severity = 0.4 + min(0.5, (1 - player.chips / starting_chips) * 0.3)
            tilt.active_stressors[STRESSOR_EXISTENTIAL_THREAT] = round(severity, 2)
            if event_bus:
                event_bus.emit(
                    TiltEvent(
                        player=player.name,
                        stressor_type=STRESSOR_EXISTENTIAL_THREAT,
                        description=f"Chip stack critical: {player.chips} chips",
                        severity=severity,
                    )
                )

        if not player.folded:
            prev = tilt.active_stressors.get(STRESSOR_REPEATED_FAILURE, 0.2)
            severity = min(1.0, prev + 0.05)
            tilt.active_stressors[STRESSOR_REPEATED_FAILURE] = round(severity, 2)
            if event_bus:
                event_bus.emit(
                    TiltEvent(
                        player=player.name,
                        stressor_type=STRESSOR_REPEATED_FAILURE,
                        description="Lost another hand",
                        severity=severity,
                    )
                )

        if tilt.loss_streak >= 5:
            tilt.active_stressors[STRESSOR_INVISIBILITY] = 0.35
            if event_bus:
                event_bus.emit(
                    TiltEvent(
                        player=player.name,
                        stressor_type=STRESSOR_INVISIBILITY,
                        description=f"No win in {tilt.loss_streak} hands",
                        severity=0.35,
                    )
                )

        if player.hands_played >= 5:
            fold_rate = player.total_folds / max(player.hands_played, 1)
            if fold_rate > 0.6:
                tilt.active_stressors[STRESSOR_FUTILITY] = 0.3
                if event_bus:
                    event_bus.emit(
                        TiltEvent(
                            player=player.name,
                            stressor_type=STRESSOR_FUTILITY,
                            description=f"Folding too often ({fold_rate:.0%})",
                            severity=0.3,
                        )
                    )
            elif STRESSOR_FUTILITY in tilt.active_stressors:
                del tilt.active_stressors[STRESSOR_FUTILITY]
                if event_bus:
                    event_bus.emit(
                        TiltResolvedEvent(
                            player=player.name,
                            stressor_type=STRESSOR_FUTILITY,
                            reason="Fold rate recovered below 60%",
                        )
                    )

    if won and STRESSOR_EXISTENTIAL_THREAT in tilt.active_stressors:
        if player.chips >= starting_chips * 0.3:
            del tilt.active_stressors[STRESSOR_EXISTENTIAL_THREAT]
            if event_bus:
                event_bus.emit(
                    TiltResolvedEvent(
                        player=player.name,
                        stressor_type=STRESSOR_EXISTENTIAL_THREAT,
                        reason="Chips recovered above 30%",
                    )
                )

    return tilt
