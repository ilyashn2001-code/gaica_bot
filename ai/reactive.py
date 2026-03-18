from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Set

from actions.models import ActionProposal
from .fsm import TacticalMode


@dataclass(slots=True)
class ReactiveDecision:
    """
    Результат reactive-слоя.
    """

    should_override: bool
    proposal: ActionProposal

    reason: Optional[str] = None
    priority: int = 0
    tags: Set[str] = field(default_factory=set)

    forced_mode: Optional[TacticalMode] = None


class ReactiveEngine:
    """
    Проверяет критические ситуации, где нужно немедленно перебить обычную тактику.
    """

    def evaluate(self, ctx) -> ReactiveDecision:
        """
        Главный вход reactive-логики.
        Порядок проверок = приоритет.
        """

        # P1 — смертельная угроза (bullet dodge)
        decision = self._check_bullet_threat(ctx)
        if decision:
            return decision

        # P2 — гарантированное убийство / decisive action
        decision = self._check_melee_finish(ctx)
        if decision:
            return decision

        # P2 — punish stunned enemy
        decision = self._check_stunned_enemy(ctx)
        if decision:
            return decision

        # нет override → продолжаем обычную логику
        return ReactiveDecision(
            should_override=False,
            proposal=ActionProposal.idle(),  # заглушка, не используется
        )

    # -------------------------
    # CHECKS
    # -------------------------

    def _check_bullet_threat(self, ctx) -> Optional[ReactiveDecision]:
        risk = ctx.features.get("incoming_bullet_risk", 0.0)

        if risk > 0.7:
            proposal = ActionProposal.dodge(ctx)

            return ReactiveDecision(
                should_override=True,
                proposal=proposal,
                reason="bullet_evade",
                priority=100,
                tags={"danger", "bullet"},
                forced_mode=TacticalMode.BULLET_EVADE,
            )

        return None

    def _check_melee_finish(self, ctx) -> Optional[ReactiveDecision]:
        can_kick = ctx.features.get("kick_confirm_window", False)

        if can_kick:
            proposal = ActionProposal.kick(ctx)

            return ReactiveDecision(
                should_override=True,
                proposal=proposal,
                reason="melee_finish",
                priority=90,
                tags={"offense", "finish"},
                forced_mode=TacticalMode.MELEE_FINISH,
            )

        return None

    def _check_stunned_enemy(self, ctx) -> Optional[ReactiveDecision]:
        stunned = ctx.features.get("enemy_stunned_window", False)

        if stunned:
            proposal = ActionProposal.aggressive_attack(ctx)

            return ReactiveDecision(
                should_override=True,
                proposal=proposal,
                reason="punish_stunned",
                priority=85,
                tags={"offense"},
                forced_mode=TacticalMode.PUNISH_STUNNED,
            )

        return None
