from __future__ import annotations

from typing import Dict, Any

from ai.controller import TickDecisionResult
from .models import ActionCommand, ActionComposeResult, ActionProposal, Vec2


class ActionComposer:
    """
    Превращает AI proposal в итоговую внутреннюю tick-команду.

    Обязанности:
    - нормализовать move/aim;
    - заполнить пропущенные поля;
    - снять очевидные конфликты;
    - вернуть ActionCommand для validator/serializer.
    """

    def compose(self, decision: TickDecisionResult) -> ActionComposeResult:
        proposal = decision.proposal

        command = ActionCommand(
            move=self._resolve_move(proposal),
            aim=self._resolve_aim(proposal),
            shoot=bool(proposal.shoot) if proposal.shoot is not None else False,
            kick=bool(proposal.kick) if proposal.kick is not None else False,
            pickup=bool(proposal.pickup) if proposal.pickup is not None else False,
            drop=bool(proposal.drop) if proposal.drop is not None else False,
            throw=bool(proposal.throw) if proposal.throw is not None else False,
            interact=bool(proposal.interact) if proposal.interact is not None else False,
            debug_tags=self._build_debug_tags(decision, proposal),
        )

        self._resolve_conflicts(command)

        return ActionComposeResult(
            command=command,
            notes={
                "intent": proposal.intent,
                "used_reactive_override": decision.used_reactive_override,
                "selected_mode": decision.selected_mode.value,
            },
        )

    def _resolve_move(self, proposal: ActionProposal) -> Vec2:
        move = proposal.move if isinstance(proposal.move, Vec2) else Vec2.zero()
        return move.clamped(1.0)

    def _resolve_aim(self, proposal: ActionProposal) -> Vec2:
        aim = proposal.aim if isinstance(proposal.aim, Vec2) else Vec2.zero()
        if aim.length() <= 1e-9:
            return Vec2.zero()
        return aim.normalized()

    def _resolve_conflicts(self, command: ActionCommand) -> None:
        """
        Базовое разрешение конфликтов между действиями.

        MVP-правила:
        - нельзя одновременно shoot и kick;
        - pickup подавляет shoot/kick;
        - throw и drop не делаем одновременно;
        """
        if command.pickup:
            command.shoot = False
            command.kick = False
            command.throw = False
            command.drop = False

        if command.shoot and command.kick:
            # Приоритет дальнобойной атаки над melee в composer.
            # Reactive layer обычно сам выберет критичный kick отдельно.
            command.kick = False

        if command.throw and command.drop:
            command.drop = False

    def _build_debug_tags(
        self,
        decision: TickDecisionResult,
        proposal: ActionProposal,
    ) -> list[str]:
        tags = [
            f"mode:{decision.selected_mode.value}",
            f"intent:{proposal.intent}",
        ]

        if decision.used_reactive_override and decision.reactive_reason:
            tags.append(f"reactive:{decision.reactive_reason}")

        return tags
