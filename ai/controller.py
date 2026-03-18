from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from actions.models import ActionProposal
from state.models import DynamicRoundState
from state.trackers import TrackerBundle

from .fsm import TacticalMode, TacticalStateMachine
from .modes import ModeRegistry
from .reactive import ReactiveDecision, ReactiveEngine
from .utility import ModeScore, UtilityEngine


@dataclass(slots=True)
class TickDecisionContext:
    """
    Полный AI-контекст на один тик.

    Это основной объект, который передается в reactive / utility / mode handlers.
    Он собирает все уже подготовленные данные в одну структуру, чтобы:
    - не тащить 10 аргументов в каждый вызов;
    - упростить тестирование;
    - стандартизировать decision pipeline.
    """

    tick: int
    world: DynamicRoundState
    trackers: TrackerBundle
    features: Dict[str, Any]
    score_series_ours: int
    score_series_enemy: int
    round_index: int
    map_id: str
    debug_enabled: bool = False


@dataclass(slots=True)
class TickDecisionResult:
    """
    Результат работы AI-контроллера на текущем тике.

    На этом этапе это еще НЕ финальная сериализованная команда протокола,
    а внутренняя AI-структура, которую дальше сможет обработать actions-layer.
    """

    selected_mode: TacticalMode
    proposal: ActionProposal
    used_reactive_override: bool
    reactive_reason: Optional[str] = None
    utility_scores: Dict[TacticalMode, ModeScore] = field(default_factory=dict)
    decision_notes: Dict[str, Any] = field(default_factory=dict)


class AIController:
    """
    Центральный координатор AI-пайплайна.

    Обязанности:
    1. Сформировать decision context.
    2. Проверить reactive overrides.
    3. Если override не найден — запросить utility scoring.
    4. Передать scoring в FSM для выбора устойчивого режима.
    5. Получить action proposal от handler'а выбранного режима.
    6. Вернуть структурированный результат для следующего слоя.

    Важно:
    - Controller НЕ реализует детальную тактическую логику режимов.
    - Controller НЕ валидирует финальную команду протокола.
    - Controller НЕ сериализует ответ в JSON.
    """

    def __init__(
        self,
        reactive_engine: ReactiveEngine,
        utility_engine: UtilityEngine,
        tactical_fsm: TacticalStateMachine,
        mode_registry: ModeRegistry,
        *,
        debug_enabled: bool = False,
    ) -> None:
        self._reactive_engine = reactive_engine
        self._utility_engine = utility_engine
        self._tactical_fsm = tactical_fsm
        self._mode_registry = mode_registry
        self._debug_enabled = debug_enabled

    def build_context(
        self,
        *,
        world: DynamicRoundState,
        trackers: TrackerBundle,
        features: Dict[str, Any],
    ) -> TickDecisionContext:
        """
        Собирает единый decision context на текущий тик.

        Предполагается, что к этому моменту:
        - world уже обновлен;
        - trackers уже обновлены;
        - feature pipeline уже выполнен.
        """
        return TickDecisionContext(
            tick=world.tick,
            world=world,
            trackers=trackers,
            features=features,
            score_series_ours=world.series_score.self_score,
            score_series_enemy=world.series_score.enemy_score,
            round_index=world.round_index,
            map_id=world.map_id,
            debug_enabled=self._debug_enabled,
        )

    def decide(
        self,
        *,
        world: DynamicRoundState,
        trackers: TrackerBundle,
        features: Dict[str, Any],
    ) -> TickDecisionResult:
        """
        Главный entrypoint AI-решения на тик.

        Последовательность:
        1. build_context
        2. reactive scan
        3. utility scoring (если override нет)
        4. FSM mode selection
        5. mode proposal generation
        """
        ctx = self.build_context(world=world, trackers=trackers, features=features)

        reactive_decision = self._reactive_engine.evaluate(ctx)
        if reactive_decision.should_override:
            return self._build_reactive_result(ctx, reactive_decision)

        utility_scores = self._utility_engine.score_modes(ctx)
        selected_mode = self._tactical_fsm.select_mode(ctx, utility_scores)

        proposal = self._resolve_mode_proposal(ctx, selected_mode)

        return TickDecisionResult(
            selected_mode=selected_mode,
            proposal=proposal,
            used_reactive_override=False,
            reactive_reason=None,
            utility_scores=utility_scores,
            decision_notes={
                "fsm_previous_mode": self._tactical_fsm.previous_mode_name(),
                "fsm_selected_mode": selected_mode.value,
            },
        )

    def _build_reactive_result(
        self,
        ctx: TickDecisionContext,
        reactive_decision: ReactiveDecision,
    ) -> TickDecisionResult:
        """
        Упаковывает reactive override в единый TickDecisionResult.
        """
        selected_mode = reactive_decision.forced_mode or TacticalMode.REACTIVE_OVERRIDE

        return TickDecisionResult(
            selected_mode=selected_mode,
            proposal=reactive_decision.proposal,
            used_reactive_override=True,
            reactive_reason=reactive_decision.reason,
            utility_scores={},
            decision_notes={
                "reactive_priority": reactive_decision.priority,
                "reactive_tags": list(reactive_decision.tags),
                "reactive_mode": selected_mode.value,
            },
        )

    def _resolve_mode_proposal(
        self,
        ctx: TickDecisionContext,
        mode: TacticalMode,
    ) -> ActionProposal:
        """
        Получает proposal от handler'а выбранного режима.

        Если handler не зарегистрирован, используем safe fallback mode.
        """
        handler = self._mode_registry.get(mode)

        if handler is None:
            fallback_handler = self._mode_registry.get(TacticalMode.SAFE_FALLBACK)
            if fallback_handler is None:
                raise RuntimeError(
                    "ModeRegistry has no handler for selected mode and no SAFE_FALLBACK handler."
                )
            return fallback_handler.propose(ctx)

        return handler.propose(ctx)
