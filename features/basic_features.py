from __future__ import annotations

from dataclasses import dataclass
import math

from state.models import GroundWeaponState, MailboxState, Vector2
from state.world_state import WorldState


REVOLVER_MAX_AMMO = 10
UZI_MAX_AMMO = 35
KICK_RANGE = 28.0
PICKUP_RANGE = 25.0
HIGH_BULLET_RISK_DISTANCE = 40.0
MELEE_THREAT_DISTANCE = 35.0
SAFE_PICKUP_ENEMY_DISTANCE = 55.0
SAFE_MAILBOX_ENEMY_DISTANCE = 60.0


@dataclass(slots=True)
class DerivedFeatures:
    dist_enemy: float
    dist_nearest_weapon: float | None
    dist_nearest_mailbox: float | None

    self_has_weapon: bool
    enemy_has_weapon: bool
    self_weapon_type: str | None
    enemy_weapon_type: str | None

    self_ammo_ratio: float
    enemy_stunned: bool

    los_enemy: bool
    incoming_bullet_risk: float
    melee_threat: bool

    kick_confirm_window: bool
    enemy_stunned_window: bool
    free_pickup_window: bool
    mailbox_safe_hit_window: bool

    should_kite: bool
    should_commit: bool
    should_disengage: bool


def extract_basic_features(world_state: WorldState) -> DerivedFeatures:
    self_player = world_state.self_player
    enemy_player = world_state.enemy_player

    dist_enemy = distance(self_player.position, enemy_player.position)
    nearest_weapon = find_nearest_weapon(world_state)
    nearest_mailbox = find_nearest_mailbox(world_state)

    dist_nearest_weapon = (
        distance(self_player.position, nearest_weapon.position)
        if nearest_weapon is not None
        else None
    )

    dist_nearest_mailbox = (
        distance(self_player.position, nearest_mailbox.position)
        if nearest_mailbox is not None
        else None
    )

    self_has_weapon = bool(self_player.weapon_type)
    enemy_has_weapon = bool(enemy_player.weapon_type)

    self_weapon_type = self_player.weapon_type
    enemy_weapon_type = enemy_player.weapon_type

    self_ammo_ratio = calc_ammo_ratio(
        weapon_type=self_weapon_type,
        ammo=self_player.ammo,
    )

    los_enemy = has_line_of_sight(world_state)
    incoming_bullet_risk = estimate_incoming_bullet_risk(world_state)
    melee_threat = dist_enemy <= MELEE_THREAT_DISTANCE and enemy_player.alive

    kick_confirm_window = (
        enemy_player.alive
        and dist_enemy <= KICK_RANGE
        and not self_player.stunned
        and self_player.kick_cooldown_ticks <= 0
    )

    enemy_stunned_window = enemy_player.alive and enemy_player.stunned

    free_pickup_window = (
        nearest_weapon is not None
        and dist_nearest_weapon is not None
        and dist_nearest_weapon <= PICKUP_RANGE
        and dist_enemy >= SAFE_PICKUP_ENEMY_DISTANCE
        and not enemy_player.stunned
    )

    mailbox_safe_hit_window = (
        nearest_mailbox is not None
        and dist_nearest_mailbox is not None
        and dist_nearest_mailbox <= KICK_RANGE
        and dist_enemy >= SAFE_MAILBOX_ENEMY_DISTANCE
        and not self_has_weapon
    )

    should_kite = (
        self_has_weapon
        and self_weapon_type == "Revolver"
        and enemy_has_weapon
        and dist_enemy < 90.0
    )

    should_commit = (
        enemy_stunned_window
        or (self_has_weapon and los_enemy and dist_enemy < 85.0 and self_player.ammo > 0)
        or (kick_confirm_window and dist_enemy < 20.0)
    )

    should_disengage = (
        incoming_bullet_risk >= 0.8
        or (not self_has_weapon and enemy_has_weapon and dist_enemy < 80.0)
        or (self_player.hp > 0 and self_player.hp <= 20.0 and enemy_has_weapon)
    )

    return DerivedFeatures(
        dist_enemy=dist_enemy,
        dist_nearest_weapon=dist_nearest_weapon,
        dist_nearest_mailbox=dist_nearest_mailbox,
        self_has_weapon=self_has_weapon,
        enemy_has_weapon=enemy_has_weapon,
        self_weapon_type=self_weapon_type,
        enemy_weapon_type=enemy_weapon_type,
        self_ammo_ratio=self_ammo_ratio,
        enemy_stunned=enemy_player.stunned,
        los_enemy=los_enemy,
        incoming_bullet_risk=incoming_bullet_risk,
        melee_threat=melee_threat,
        kick_confirm_window=kick_confirm_window,
        enemy_stunned_window=enemy_stunned_window,
        free_pickup_window=free_pickup_window,
        mailbox_safe_hit_window=mailbox_safe_hit_window,
        should_kite=should_kite,
        should_commit=should_commit,
        should_disengage=should_disengage,
    )


def distance(a: Vector2, b: Vector2) -> float:
    return math.hypot(a.x - b.x, a.y - b.y)


def calc_ammo_ratio(weapon_type: str | None, ammo: int) -> float:
    if weapon_type == "Revolver":
        return clamp(ammo / REVOLVER_MAX_AMMO, 0.0, 1.0)

    if weapon_type == "Uzi":
        return clamp(ammo / UZI_MAX_AMMO, 0.0, 1.0)

    return 0.0


def find_nearest_weapon(world_state: WorldState) -> GroundWeaponState | None:
    self_pos = world_state.self_player.position

    available_weapons = [w for w in world_state.ground_weapons if w.available]
    if not available_weapons:
        return None

    return min(
        available_weapons,
        key=lambda weapon: distance(self_pos, weapon.position),
    )


def find_nearest_mailbox(world_state: WorldState) -> MailboxState | None:
    self_pos = world_state.self_player.position

    active_mailboxes = [m for m in world_state.mailboxes if m.active]
    if not active_mailboxes:
        return None

    return min(
        active_mailboxes,
        key=lambda mailbox: distance(self_pos, mailbox.position),
    )


def estimate_incoming_bullet_risk(world_state: WorldState) -> float:
    """
    Грубая эвристика для MVP:
    - смотрим только на активные пули не от нас;
    - если пуля близко и летит примерно в нашу сторону, риск повышается.
    """
    self_pos = world_state.self_player.position
    risk = 0.0

    for bullet in world_state.bullets:
        if not bullet.active:
            continue

        if bullet.owner_slot == world_state.match.my_slot:
            continue

        bullet_dist = distance(self_pos, bullet.position)
        if bullet_dist > HIGH_BULLET_RISK_DISTANCE:
            continue

        to_self_x = self_pos.x - bullet.position.x
        to_self_y = self_pos.y - bullet.position.y

        dot = bullet.velocity.x * to_self_x + bullet.velocity.y * to_self_y
        if dot <= 0:
            continue

        local_risk = 1.0 - clamp(bullet_dist / HIGH_BULLET_RISK_DISTANCE, 0.0, 1.0)
        risk = max(risk, local_risk)

    return clamp(risk, 0.0, 1.0)


def has_line_of_sight(world_state: WorldState) -> bool:
    """
    MVP-версия:
    Пока считаем LOS = True.

    Потом сюда можно добавить:
    - проверку пересечения отрезка self->enemy со стенами;
    - учет стекла/дверей/разрушаемых объектов;
    - special handling для временно открытых дверей.
    """
    return True


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))
