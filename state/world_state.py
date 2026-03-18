from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from actions.models import BotAction
from state.models import (
    BulletState,
    DestructibleState,
    EffectState,
    GroundWeaponState,
    MailboxState,
    MatchContext,
    ObstacleState,
    PlayerState,
    RoundContext,
    as_vector2,
)


@dataclass
class WorldState:
    match: MatchContext = field(default_factory=MatchContext)
    round: RoundContext = field(default_factory=RoundContext)

    tick_index: int = 0

    self_player: PlayerState = field(default_factory=PlayerState)
    enemy_player: PlayerState = field(default_factory=PlayerState)

    ground_weapons: list[GroundWeaponState] = field(default_factory=list)
    bullets: list[BulletState] = field(default_factory=list)
    obstacles: list[ObstacleState] = field(default_factory=list)
    destructibles: list[DestructibleState] = field(default_factory=list)
    mailboxes: list[MailboxState] = field(default_factory=list)
    effects: list[EffectState] = field(default_factory=list)

    map_raw: dict[str, Any] = field(default_factory=dict)

    last_valid_action: BotAction = field(default_factory=BotAction.idle)

    is_match_active: bool = False
    is_round_active: bool = False

    def apply_match_start(self, message: dict[str, Any]) -> None:
        payload = self._payload(message)

        self.match.my_slot = int(payload.get("slot", -1))
        self.match.tick_rate = int(payload.get("tickRate", 30))

        self.is_match_active = True

    def apply_round_start(self, message: dict[str, Any]) -> None:
        payload = self._payload(message)

        self.round.round_index = int(payload.get("roundIndex", -1))
        self.round.map_id = str(payload.get("mapId", ""))
        self.round.map_index = int(payload.get("mapIndex", -1))

        score = payload.get("score", {})
        if isinstance(score, dict):
            self.round.score_self = int(score.get("self", 0))
            self.round.score_enemy = int(score.get("enemy", 0))

        self.map_raw = payload.get("map", {}) if isinstance(payload.get("map"), dict) else {}
        self.tick_index = 0
        self.is_round_active = True

        self.ground_weapons.clear()
        self.bullets.clear()
        self.effects.clear()

    def apply_tick(self, message: dict[str, Any]) -> None:
        payload = self._payload(message)

        self.tick_index = int(payload.get("tick", self.tick_index + 1))

        self.self_player = self._parse_player(payload.get("self", {}))
        self.enemy_player = self._parse_player(payload.get("enemy", {}))

        self.ground_weapons = self._parse_ground_weapons(payload.get("weapons", []))
        self.bullets = self._parse_bullets(payload.get("bullets", []))
        self.obstacles = self._parse_obstacles(payload.get("obstacles", []))
        self.destructibles = self._parse_destructibles(payload.get("destructibles", []))
        self.mailboxes = self._parse_mailboxes(payload.get("mailboxes", []))
        self.effects = self._parse_effects(payload.get("effects", []))

    def apply_round_end(self, message: dict[str, Any]) -> None:
        payload = self._payload(message)

        score = payload.get("score", {})
        if isinstance(score, dict):
            self.round.score_self = int(score.get("self", self.round.score_self))
            self.round.score_enemy = int(score.get("enemy", self.round.score_enemy))

        self.is_round_active = False

    def apply_match_end(self, message: dict[str, Any]) -> None:
        self.is_match_active = False
        self.is_round_active = False

    def get_safe_fallback_action(self) -> BotAction:
        """
        Безопасная команда по умолчанию.
        Пока — просто idle с сохранением последнего направления aim.
        """
        return BotAction(
            move_x=0.0,
            move_y=0.0,
            aim_x=self.last_valid_action.aim_x,
            aim_y=self.last_valid_action.aim_y,
            shoot=False,
            kick=False,
            pickup=False,
            drop=False,
            throw=False,
            interact=False,
        )

    @staticmethod
    def _payload(message: dict[str, Any]) -> dict[str, Any]:
        payload = message.get("payload", {})
        return payload if isinstance(payload, dict) else {}

    def _parse_player(self, data: dict[str, Any]) -> PlayerState:
        if not isinstance(data, dict):
            return PlayerState()

        return PlayerState(
            player_id=str(data.get("id", "")),
            slot=int(data.get("slot", -1)),
            position=as_vector2(data.get("position")),
            velocity=as_vector2(data.get("velocity")),
            aim=as_vector2(data.get("aim")),
            hp=float(data.get("hp", 0.0)),
            radius=float(data.get("radius", 10.0)),
            alive=bool(data.get("alive", True)),
            stunned=bool(data.get("stunned", False)),
            weapon_type=data.get("weaponType"),
            ammo=int(data.get("ammo", 0)),
            kick_cooldown_ticks=int(data.get("kickCooldownTicks", 0)),
            weapon_cooldown_ticks=int(data.get("weaponCooldownTicks", 0)),
        )

    def _parse_ground_weapons(self, items: Any) -> list[GroundWeaponState]:
        if not isinstance(items, list):
            return []

        result: list[GroundWeaponState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                GroundWeaponState(
                    weapon_id=str(item.get("id", "")),
                    weapon_type=str(item.get("weaponType", "")),
                    position=as_vector2(item.get("position")),
                    ammo=int(item.get("ammo", 0)),
                    available=bool(item.get("available", True)),
                )
            )
        return result

    def _parse_bullets(self, items: Any) -> list[BulletState]:
        if not isinstance(items, list):
            return []

        result: list[BulletState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                BulletState(
                    bullet_id=str(item.get("id", "")),
                    position=as_vector2(item.get("position")),
                    velocity=as_vector2(item.get("velocity")),
                    owner_slot=int(item.get("ownerSlot", -1)),
                    active=bool(item.get("active", True)),
                )
            )
        return result

    def _parse_obstacles(self, items: Any) -> list[ObstacleState]:
        if not isinstance(items, list):
            return []

        result: list[ObstacleState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                ObstacleState(
                    obstacle_id=str(item.get("id", "")),
                    position=as_vector2(item.get("position")),
                    size=as_vector2(item.get("size")),
                    obstacle_type=str(item.get("type", "")),
                )
            )
        return result

    def _parse_destructibles(self, items: Any) -> list[DestructibleState]:
        if not isinstance(items, list):
            return []

        result: list[DestructibleState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                DestructibleState(
                    object_id=str(item.get("id", "")),
                    position=as_vector2(item.get("position")),
                    size=as_vector2(item.get("size")),
                    hp=float(item.get("hp", 0.0)),
                    destroyed=bool(item.get("destroyed", False)),
                    object_type=str(item.get("type", "")),
                )
            )
        return result

    def _parse_mailboxes(self, items: Any) -> list[MailboxState]:
        if not isinstance(items, list):
            return []

        result: list[MailboxState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                MailboxState(
                    mailbox_id=str(item.get("id", "")),
                    position=as_vector2(item.get("position")),
                    cooldown_ticks=int(item.get("cooldownTicks", 0)),
                    active=bool(item.get("active", True)),
                )
            )
        return result

    def _parse_effects(self, items: Any) -> list[EffectState]:
        if not isinstance(items, list):
            return []

        result: list[EffectState] = []
        for item in items:
            if not isinstance(item, dict):
                continue

            result.append(
                EffectState(
                    effect_type=str(item.get("type", "")),
                    source_slot=int(item.get("sourceSlot", -1)),
                    target_slot=int(item.get("targetSlot", -1)),
                    ttl_ticks=int(item.get("ttlTicks", 0)),
                )
            )
        return result
