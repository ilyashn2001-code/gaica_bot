from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TickCounter:
    value: int = 0

    def reset(self) -> None:
        self.value = 0

    def step(self) -> None:
        self.value += 1


@dataclass
class CombatTrackers:
    ticks_since_enemy_seen_armed: int = 999999
    ticks_since_self_had_weapon: int = 999999
    ticks_enemy_stunned: int = 0
    ticks_high_bullet_risk: int = 0
    ticks_since_mailbox_interaction: int = 999999

    def reset_for_new_round(self) -> None:
        self.ticks_since_enemy_seen_armed = 999999
        self.ticks_since_self_had_weapon = 999999
        self.ticks_enemy_stunned = 0
        self.ticks_high_bullet_risk = 0
        self.ticks_since_mailbox_interaction = 999999

    def update(
        self,
        enemy_has_weapon: bool,
        self_has_weapon: bool,
        enemy_stunned: bool,
        high_bullet_risk: bool,
        mailbox_interaction_happened: bool = False,
    ) -> None:
        if enemy_has_weapon:
            self.ticks_since_enemy_seen_armed = 0
        else:
            self.ticks_since_enemy_seen_armed += 1

        if self_has_weapon:
            self.ticks_since_self_had_weapon = 0
        else:
            self.ticks_since_self_had_weapon += 1

        if enemy_stunned:
            self.ticks_enemy_stunned += 1
        else:
            self.ticks_enemy_stunned = 0

        if high_bullet_risk:
            self.ticks_high_bullet_risk += 1
        else:
            self.ticks_high_bullet_risk = 0

        if mailbox_interaction_happened:
            self.ticks_since_mailbox_interaction = 0
        else:
            self.ticks_since_mailbox_interaction += 1


@dataclass
class ModeTrackers:
    current_mode: str = "idle"
    ticks_in_mode: int = 0
    previous_mode: str = "idle"

    def switch_mode(self, new_mode: str) -> None:
        if new_mode == self.current_mode:
            self.ticks_in_mode += 1
            return

        self.previous_mode = self.current_mode
        self.current_mode = new_mode
        self.ticks_in_mode = 0


@dataclass
class TrackerBundle:
    combat: CombatTrackers = field(default_factory=CombatTrackers)
    mode: ModeTrackers = field(default_factory=ModeTrackers)

    def reset_for_new_round(self) -> None:
        self.combat.reset_for_new_round()
        self.mode = ModeTrackers()
