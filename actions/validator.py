from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import List

from .models import ActionCommand, Vec2


@dataclass(slots=True)
class ValidationResult:
    is_valid: bool
    command: ActionCommand
    used_fallback: bool = False
    issues: List[str] = field(default_factory=list)


class ActionValidator:
    """
    Проверяет итоговую команду перед сериализацией и отправкой.

    MVP-фокус:
    - базовая техническая корректность;
    - снятие опасных конфликтов;
    - safe fallback вместо падения.
    """

    def validate(self, command: ActionCommand) -> ValidationResult:
        issues: list[str] = []

        if not self._is_finite_vec(command.move):
            issues.append("move vector contains non-finite values")

        if not self._is_finite_vec(command.aim):
            issues.append("aim vector contains non-finite values")

        if command.move.length() > 1.000001:
            issues.append("move vector exceeds normalized limit")

        if command.aim.length() > 1.000001:
            issues.append("aim vector exceeds normalized limit")

        action_flags = [
            command.shoot,
            command.kick,
            command.pickup,
            command.drop,
            command.throw,
            command.interact,
        ]

        if sum(1 for flag in action_flags if flag) > 2:
            issues.append("too many simultaneous action flags")

        if command.shoot and command.kick:
            issues.append("shoot and kick cannot be active together")

        if command.pickup and (command.shoot or command.kick or command.throw or command.drop):
            issues.append("pickup conflicts with combat/inventory actions")

        if command.throw and command.drop:
            issues.append("throw and drop cannot be active together")

        if issues:
            fallback = self._safe_fallback(command)
            return ValidationResult(
                is_valid=False,
                command=fallback,
                used_fallback=True,
                issues=issues,
            )

        normalized = self._normalize_command(command)
        return ValidationResult(
            is_valid=True,
            command=normalized,
            used_fallback=False,
            issues=[],
        )

    def _normalize_command(self, command: ActionCommand) -> ActionCommand:
        return ActionCommand(
            move=command.move.clamped(1.0),
            aim=command.aim.normalized() if command.aim.length() > 1e-9 else Vec2.zero(),
            shoot=command.shoot,
            kick=command.kick,
            pickup=command.pickup,
            drop=command.drop,
            throw=command.throw,
            interact=command.interact,
            debug_tags=list(command.debug_tags),
        )

    def _safe_fallback(self, original: ActionCommand) -> ActionCommand:
        """
        Безопасная команда по умолчанию.

        Принцип:
        - не стреляем;
        - не делаем конфликтных действий;
        - сохраняем только безопасное движение;
        - aim можно оставить нулевым.
        """
        safe_move = original.move if self._is_finite_vec(original.move) else Vec2.zero()
        safe_move = safe_move.clamped(1.0)

        return ActionCommand(
            move=safe_move,
            aim=Vec2.zero(),
            shoot=False,
            kick=False,
            pickup=False,
            drop=False,
            throw=False,
            interact=False,
            debug_tags=list(original.debug_tags) + ["validator:fallback"],
        )

    def _is_finite_vec(self, vec: Vec2) -> bool:
        return isfinite(vec.x) and isfinite(vec.y)
