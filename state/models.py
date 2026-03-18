from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class Vector2:
    x: float = 0.0
    y: float = 0.0


@dataclass(slots=True)
class PlayerState:
    player_id: str = ""
    slot: int = -1

    position: Vector2 = field(default_factory=Vector2)
    velocity: Vector2 = field(default_factory=Vector2)
    aim: Vector2 = field(default_factory=Vector2)

    hp: float = 0.0
    radius: float = 10.0

    alive: bool = True
    stunned: bool = False

    weapon_type: str | None = None
    ammo: int = 0

    kick_cooldown_ticks: int = 0
    weapon_cooldown_ticks: int = 0


@dataclass(slots=True)
class GroundWeaponState:
    weapon_id: str = ""
    weapon_type: str = ""
    position: Vector2 = field(default_factory=Vector2)
    ammo: int = 0
    available: bool = True


@dataclass(slots=True)
class BulletState:
    bullet_id: str = ""
    position: Vector2 = field(default_factory=Vector2)
    velocity: Vector2 = field(default_factory=Vector2)
    owner_slot: int = -1
    active: bool = True


@dataclass(slots=True)
class ObstacleState:
    obstacle_id: str = ""
    position: Vector2 = field(default_factory=Vector2)
    size: Vector2 = field(default_factory=Vector2)
    obstacle_type: str = ""


@dataclass(slots=True)
class DestructibleState:
    object_id: str = ""
    position: Vector2 = field(default_factory=Vector2)
    size: Vector2 = field(default_factory=Vector2)
    hp: float = 0.0
    destroyed: bool = False
    object_type: str = ""


@dataclass(slots=True)
class MailboxState:
    mailbox_id: str = ""
    position: Vector2 = field(default_factory=Vector2)
    cooldown_ticks: int = 0
    active: bool = True


@dataclass(slots=True)
class EffectState:
    effect_type: str = ""
    source_slot: int = -1
    target_slot: int = -1
    ttl_ticks: int = 0


@dataclass(slots=True)
class MatchContext:
    my_slot: int = -1
    tick_rate: int = 30


@dataclass(slots=True)
class RoundContext:
    round_index: int = -1
    map_id: str = ""
    map_index: int = -1
    score_self: int = 0
    score_enemy: int = 0


def as_vector2(data: dict[str, Any] | None) -> Vector2:
    """
    Безопасное преобразование словаря вида {"x": ..., "y": ...}
    в Vector2.
    """
    if not isinstance(data, dict):
        return Vector2()

    return Vector2(
        x=float(data.get("x", 0.0)),
        y=float(data.get("y", 0.0)),
    )
