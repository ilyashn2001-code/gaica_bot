from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Protocol

from actions.models import ActionProposal
from ai.fsm import TacticalFSM, TacticalState
from ai.reactive import ReactiveDecision, ReactiveEngine
from ai.utility import UtilityDecision, UtilityScorer
from state.models import DynamicRoundState, MatchContext
from state.trackers import TrackerBundle


@dataclass(slots=True)
class AIContext:
    """
    Полный контекст одного тика, который нужен AI-слою.

    Это единая точка передачи данных между:
    - reactive layer
    - utility scoring
    - FSM
    - modes
    """

    tick_index: int
    match_context: MatchContext
    round_state: DynamicRoundState
    trackers: TrackerBundle
    features: Dict[str, Any]
    settings: Any

    @property
    def self_state(self) -> Any:
        return self.round_state.self_state

    @property
    def enemy_state(self) -> Any:
        return self.round_state.enemy_state

    @property
    def round_index(self) -> int:
        return self.round_state.round_index

    @property
    def map_id(self) -> str:
        return self.round_state.map_id


@dataclass(slots=True)
class AIDecision:
    """
    Результат работы AI-слоя за один тик.

    Важно: это еще не финальная сериализуемая игровая команда.
    Это внутреннее AI-решение, которое затем пройдет через action layer.
    """

    tick_index: int
    selected_mode: str
    tactical_state: TacticalState
    action_proposal: ActionProposal

    source: str  # reactive | tactical | fallback
    reactive_reason: Optional[str] = None

    utility_scores: Dict[str, float] = field(default_factory=dict)
    strategic_tags: Dict[str, Any] = field(default_factory=dict)
    debug: Dict[str, Any] = field(default_factory=dict)


class ModeHandler(Protocol):
    """
    Контракт для обработчика режима поведения.

    Каждый режим в modes.py должен уметь:
    - иметь уникальное имя;
    - по AIContext возвращать ActionProposal.
    """

    mode_name: str

    def build_action(self, ctx: AIContext, tactical_state: TacticalState) -> ActionProposal:
        ...


class AIController:
    """
    Центральный оркестратор AI-слоя.

    Порядок работы:
    1. Reactive scan
    2. Utility evaluation
    3. FSM update
    4. Mode action build
    5. Возврат AIDecision

    Этот класс специально не содержит деталей конкретной тактики.
    Его задача — собирать решение из специализированных подсистем.
    """

    def __init__(
        self,
        reactive_engine: ReactiveEngine,
        utility_scorer: UtilityScorer,
        tactical_fsm: TacticalFSM,
        mode_handlers: Dict[str, ModeHandler],
    ) -> None:
        self._reactive_engine = reactive_engine
        self._utility_scorer = utility_scorer
        self._tactical_fsm = tactical_fsm
        self._mode_handlers = dict(mode_handlers)

    def decide(self, ctx: AIContext) -> AIDecision:
        """
        Главная точка входа AI-слоя на одном тике.
        """

        # ------------------------------------------------------------------
        # P0. Базовая валидация жизнеспособности контекста
        # ------------------------------------------------------------------
        if not self._is_context_actionable(ctx):
            fallback = self._build_safe_idle_fallback(ctx, reason="invalid_or_dead_context")
            return AIDecision(
                tick_index=ctx.tick_index,
                selected_mode="fallback_idle",
                tactical_state=self._tactical_fsm.current_state,
                action_proposal=fallback,
                source="fallback",
                reactive_reason="invalid_or_dead_context",
                debug={"stage": "p0_validation"},
            )

        # ------------------------------------------------------------------
        # P1-P2. Reactive override
        # ------------------------------------------------------------------
        reactive_decision = self._reactive_engine.evaluate(ctx)
        if reactive_decision.triggered:
            return self._build_reactive_result(ctx, reactive_decision)

        # ------------------------------------------------------------------
        # P3-P6. Tactical / utility path
        # ------------------------------------------------------------------
        utility_decision = self._utility_scorer.evaluate(ctx, self._tactical_fsm.current_state)

        transition_result = self._tactical_fsm.update(
            ctx=ctx,
            desired_mode=utility_decision.selected_mode,
            utility_decision=utility_decision,
        )

        active_mode = transition_result.active_mode
        proposal = self._build_mode_action(ctx, active_mode, transition_result.new_state)

        return AIDecision(
            tick_index=ctx.tick_index,
            selected_mode=active_mode,
            tactical_state=transition_result.new_state,
            action_proposal=proposal,
            source="tactical",
            utility_scores={name: score.score for name, score in utility_decision.mode_scores.items()},
            strategic_tags=dict(utility_decision.tags),
            debug={
                "stage": "tactical",
                "desired_mode": utility_decision.selected_mode,
                "fsm_transition": transition_result.transition_kind,
                "fsm_reason": transition_result.reason,
            },
        )

    def _build_reactive_result(self, ctx: AIContext, decision: ReactiveDecision) -> AIDecision:
        """
        Упаковка reactive override в стандартный AIDecision.
        """
        tactical_state = self._tactical_fsm.current_state

        return AIDecision(
            tick_index=ctx.tick_index,
            selected_mode=decision.override_mode,
            tactical_state=tactical_state,
            action_proposal=decision.action_proposal,
            source="reactive",
            reactive_reason=decision.reason.value,
            debug={
                "stage": "reactive",
                "priority": decision.priority,
                "details": dict(decision.details),
            },
        )

    def _build_mode_action(
        self,
        ctx: AIContext,
        mode_name: str,
        tactical_state: TacticalState,
    ) -> ActionProposal:
        """
        Построение action proposal через обработчик режима.
        """
        handler = self._mode_handlers.get(mode_name)
        if handler is None:
            return self._build_safe_idle_fallback(ctx, reason=f"missing_mode_handler:{mode_name}")

        proposal = handler.build_action(ctx, tactical_state)

        if proposal is None:
            return self._build_safe_idle_fallback(ctx, reason=f"mode_returned_none:{mode_name}")

        return proposal

    def _is_context_actionable(self, ctx: AIContext) -> bool:
        """
        Минимальная sanity-проверка перед запуском AI.

        Здесь без фанатизма:
        - self_state должен быть доступен
        - enemy_state должен быть доступен
        - бот должен быть жив
        """
        self_state = getattr(ctx.round_state, "self_state", None)
        enemy_state = getattr(ctx.round_state, "enemy_state", None)

        if self_state is None or enemy_state is None:
            return False

        is_alive = getattr(self_state, "is_alive", True)
        return bool(is_alive)

    def _build_safe_idle_fallback(self, ctx: AIContext, reason: str) -> ActionProposal:
        """
        Временный безопасный fallback на уровне AI.

        Важно:
        это НЕ финальный safety controller из отдельного слоя actions/safety,
        а локальная страховка, чтобы AI никогда не падал в пустоту.
        """
        return ActionProposal(
            move=(0.0, 0.0),
            aim=None,
            shoot=False,
            kick=False,
            pickup=False,
            drop=False,
            throw=False,
            interact=False,
            meta={
                "source": "ai_fallback",
                "reason": reason,
                "tick": ctx.tick_index,
            },
        )
