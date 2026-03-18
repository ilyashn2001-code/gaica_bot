from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from .fsm import TacticalMode


@dataclass(slots=True)
class ModeScore:
    mode: TacticalMode
    score: float


class UtilityEngine:
    """
    Считает utility score для каждого режима.
    """

    def score_modes(self, ctx) -> Dict[TacticalMode, ModeScore]:
        scores: Dict[TacticalMode, ModeScore] = {}

        for mode in TacticalMode:
            score = self._score_mode(ctx, mode)
            scores[mode] = ModeScore(mode=mode, score=score)

        return scores

    def _score_mode(self, ctx, mode: TacticalMode) -> float:
        f = ctx.features

        # 🔹 примеры скоринга

        if mode == TacticalMode.SEEK_WEAPON:
            return (1 - f.get("self_has_weapon", 0)) * 10

        if mode == TacticalMode.AGGRESSIVE_ATTACK:
            return f.get("should_commit", 0) * 8

        if mode == TacticalMode.SAFE_HARASS:
            return f.get("dist_enemy", 0) * 0.1

        if mode == TacticalMode.RETREAT:
            return f.get("should_disengage", 0) * 10

        if mode == TacticalMode.HOLD_DISTANCE:
            return f.get("should_kite", 0) * 7

        return 0.0
