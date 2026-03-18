from __future__ import annotations

from enum import Enum
from typing import Dict

from .utility import ModeScore


class TacticalMode(str, Enum):
    SEEK_WEAPON = "seek_weapon"
    AGGRESSIVE_ATTACK = "aggressive_attack"
    SAFE_HARASS = "safe_harass"
    RETREAT = "retreat"
    HOLD_DISTANCE = "hold_distance"
    BULLET_EVADE = "bullet_evade"
    MELEE_FINISH = "melee_finish"
    PUNISH_STUNNED = "punish_stunned"
    SAFE_FALLBACK = "safe_fallback"
    REACTIVE_OVERRIDE = "reactive_override"


class TacticalStateMachine:
    """
    Удерживает текущий режим и предотвращает jitter.
    """

    def __init__(self):
        self._current_mode: TacticalMode = TacticalMode.SAFE_FALLBACK
        self._last_switch_tick: int = 0

    def select_mode(
        self,
        ctx,
        scores: Dict[TacticalMode, ModeScore],
    ) -> TacticalMode:

        best_mode = max(scores.values(), key=lambda x: x.score).mode

        # hysteresis
        if best_mode != self._current_mode:
            if self._should_switch(ctx, best_mode, scores):
                self._current_mode = best_mode
                self._last_switch_tick = ctx.tick

        return self._current_mode

    def _should_switch(self, ctx, new_mode, scores) -> bool:
        current_score = scores[self._current_mode].score
        new_score = scores[new_mode].score

        # порог переключения
        return new_score > current_score * 1.2

    def previous_mode_name(self) -> str:
        return self._current_mode.value
