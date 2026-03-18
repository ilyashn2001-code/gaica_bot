from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt
from typing import Any, Dict, Optional


@dataclass(frozen=True, slots=True)
class Vec2:
    x: float
    y: float

    def length(self) -> float:
        return sqrt(self.x * self.x + self.y * self.y)

    def normalized(self) -> "Vec2":
        length = self.length()
        if length <= 1e-9:
            return Vec2(0.0, 0.0)
        return Vec2(self.x / length, self.y / length)

    def clamped(self, max_length: float = 1.0) -> "Vec2":
        length = self.length()
        if length <= max_length or length <= 1e-9:
            return self
        scale = max_length / length
        return Vec2(self.x * scale, self.y * scale)

    @staticmethod
    def zero() -> "Vec2":
        return Vec2(0.0, 0.0)


@dataclass(slots=True)
class ActionCommand:
    """
    Финальная внутренняя команда на тик.

    Это уже почти wire-level сущность, но пока еще без сериализации.
    Именно ее потом можно отдать в protocol/serializer.py.
    """

    move: Vec2 = field(default_factory=Vec2.zero)
    aim: Vec2 = field(default_factory=Vec2.zero)

    shoot: bool = False
    kick: bool = False
    pickup: bool = False
    drop: bool = False
    throw: bool = False
    interact: bool = False

    debug_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "move": {"x": self.move.x, "y": self.move.y},
            "aim": {"x": self.aim.x, "y": self.aim.y},
            "shoot": self.shoot,
            "kick": self.kick,
            "pickup": self.pickup,
            "drop": self.drop,
            "throw": self.throw,
            "interact": self.interact,
        }


@dataclass(slots=True)
class ActionProposal:
    """
    Намерение от AI-слоя.

    Важно:
    - это еще не обязательно полностью готовая и валидная команда;
    - proposal может быть высокоуровневым;
    - composer уточняет и нормализует его до ActionCommand.
    """

    intent: str
    move: Optional[Vec2] = None
    aim: Optional[Vec2] = None

    shoot: Optional[bool] = None
    kick: Optional[bool] = None
    pickup: Optional[bool] = None
    drop: Optional[bool] = None
    throw: Optional[bool] = None
    interact: Optional[bool] = None

    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def idle(cls) -> "ActionProposal":
        return cls(intent="idle", move=Vec2.zero(), aim=Vec2.zero())

    @classmethod
    def dodge(cls, ctx) -> "ActionProposal":
        dodge_dir = ctx.features.get("suggested_dodge_direction", Vec2(-1.0, 0.0))
        if not isinstance(dodge_dir, Vec2):
            dodge_dir = Vec2(-1.0, 0.0)
        return cls(
            intent="dodge",
            move=dodge_dir.clamped(1.0),
            aim=ctx.features.get("enemy_aim_direction", Vec2.zero()),
            metadata={"source": "reactive", "reason": "incoming_bullet"},
        )

    @classmethod
    def kick(cls, ctx) -> "ActionProposal":
        aim = ctx.features.get("enemy_direction", Vec2(1.0, 0.0))
        if not isinstance(aim, Vec2):
            aim = Vec2(1.0, 0.0)
        return cls(
            intent="kick",
            move=Vec2.zero(),
            aim=aim.normalized(),
            kick=True,
            metadata={"source": "reactive", "reason": "kick_confirm_window"},
        )

    @classmethod
    def aggressive_attack(cls, ctx) -> "ActionProposal":
        aim = ctx.features.get("enemy_direction", Vec2(1.0, 0.0))
        move = ctx.features.get("pressure_move_direction", aim)
        if not isinstance(aim, Vec2):
            aim = Vec2(1.0, 0.0)
        if not isinstance(move, Vec2):
            move = aim
        return cls(
            intent="aggressive_attack",
            move=move.clamped(1.0),
            aim=aim.normalized(),
            shoot=bool(ctx.features.get("guaranteed_shot_window", False)),
            metadata={"source": "reactive", "reason": "punish_stunned_enemy"},
        )

    @classmethod
    def move_to_weapon(cls, ctx) -> "ActionProposal":
        move = ctx.features.get("nearest_weapon_direction", Vec2.zero())
        if not isinstance(move, Vec2):
            move = Vec2.zero()
        aim = ctx.features.get("enemy_direction", Vec2.zero())
        if not isinstance(aim, Vec2):
            aim = Vec2.zero()
        return cls(
            intent="seek_weapon",
            move=move.clamped(1.0),
            aim=aim.normalized() if aim.length() > 0 else Vec2.zero(),
            pickup=bool(ctx.features.get("free_pickup_window", False)),
            metadata={"source": "mode", "mode": "seek_weapon"},
        )

    @classmethod
    def attack(cls, ctx) -> "ActionProposal":
        aim = ctx.features.get("enemy_direction", Vec2(1.0, 0.0))
        move = ctx.features.get("attack_move_direction", Vec2.zero())
        if not isinstance(aim, Vec2):
            aim = Vec2(1.0, 0.0)
        if not isinstance(move, Vec2):
            move = Vec2.zero()
        return cls(
            intent="attack",
            move=move.clamped(1.0),
            aim=aim.normalized(),
            shoot=bool(ctx.features.get("los_enemy", False) and ctx.features.get("self_has_weapon", False)),
            metadata={"source": "mode", "mode": "aggressive_attack"},
        )

    @classmethod
    def retreat(cls, ctx) -> "ActionProposal":
        move = ctx.features.get("retreat_direction", Vec2(-1.0, 0.0))
        if not isinstance(move, Vec2):
            move = Vec2(-1.0, 0.0)
        aim = ctx.features.get("enemy_direction", Vec2.zero())
        if not isinstance(aim, Vec2):
            aim = Vec2.zero()
        return cls(
            intent="retreat",
            move=move.clamped(1.0),
            aim=aim.normalized() if aim.length() > 0 else Vec2.zero(),
            shoot=False,
            metadata={"source": "mode", "mode": "retreat"},
        )


@dataclass(slots=True)
class ActionComposeResult:
    """
    Результат композиции команды на тик.
    """

    command: ActionCommand
    notes: Dict[str, Any] = field(default_factory=dict)
