from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class RuntimeSettings:
    """
    Общие настройки исполнения бота.
    """

    tick_rate: int = 30
    max_tick_wait_seconds: float = 1.0
    max_match_wait_seconds: float = 60.0
    round_cpu_limit_seconds: float = 120.0
    round_wall_time_limit_seconds: float = 180.0
    enable_debug: bool = False


@dataclass(slots=True, frozen=True)
class ReactiveSettings:
    """
    Пороги и правила для reactive-слоя.
    """

    bullet_danger_threshold: float = 0.70
    melee_finish_enabled: bool = True
    stunned_enemy_punish_enabled: bool = True
    force_evade_priority: int = 100
    force_melee_priority: int = 90
    force_stunned_priority: int = 85


@dataclass(slots=True, frozen=True)
class UtilitySettings:
    """
    Настройки utility scoring.

    Здесь живут веса режимов и базовые коэффициенты,
    чтобы не держать их захардкоженными в ai/utility.py.
    """

    seek_weapon_base_weight: float = 10.0
    aggressive_attack_base_weight: float = 8.0
    safe_harass_distance_weight: float = 0.10
    retreat_base_weight: float = 10.0
    hold_distance_base_weight: float = 7.0

    low_resource_penalty: float = 2.0
    no_weapon_bonus: float = 4.0
    timeout_play_bonus: float = 3.0


@dataclass(slots=True, frozen=True)
class FSMSettings:
    """
    Настройки устойчивости tactical mode selection.
    """

    mode_switch_score_ratio: float = 1.20
    min_ticks_between_switches: int = 3
    allow_immediate_switch_on_emergency_exit: bool = True
    default_mode_name: str = "safe_fallback"


@dataclass(slots=True, frozen=True)
class ActionSettings:
    """
    Настройки action composition / validation.
    """

    max_move_vector_length: float = 1.0
    max_aim_vector_length: float = 1.0
    max_simultaneous_action_flags: int = 2

    pickup_blocks_combat_actions: bool = True
    shoot_overrides_kick: bool = True
    throw_blocks_drop: bool = True

    fallback_zero_aim: bool = True
    fallback_cancel_all_action_flags: bool = True


@dataclass(slots=True, frozen=True)
class LoggingSettings:
    """
    Настройки decision trace и логирования.
    """

    enable_decision_trace: bool = True
    enable_utility_score_dump: bool = True
    enable_reactive_reason_logging: bool = True
    enable_mode_switch_logging: bool = True
    stderr_log_level: str = "INFO"


@dataclass(slots=True, frozen=True)
class BotSettings:
    """
    Главный агрегирующий объект конфигурации бота.
    """

    runtime: RuntimeSettings = field(default_factory=RuntimeSettings)
    reactive: ReactiveSettings = field(default_factory=ReactiveSettings)
    utility: UtilitySettings = field(default_factory=UtilitySettings)
    fsm: FSMSettings = field(default_factory=FSMSettings)
    actions: ActionSettings = field(default_factory=ActionSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)


def build_default_settings() -> BotSettings:
    """
    Возвращает стандартную конфигурацию бота.

    Пока это кодовый default-profile.
    Позже здесь можно:
    - читать значения из JSON;
    - подмешивать env overrides;
    - выбирать preset под карты/режимы.
    """
    return BotSettings()
