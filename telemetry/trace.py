from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from actions.composer import ActionComposeResult
from actions.validator import ValidationResult
from ai.controller import TickDecisionContext, TickDecisionResult
from .logger import BotLogger


@dataclass(slots=True)
class DecisionTraceEntry:
    """
    Структурированная запись decision pipeline на один тик.
    """

    tick: int
    round_index: int
    map_id: str

    selected_mode: str
    used_reactive_override: bool
    reactive_reason: Optional[str]

    proposal_intent: str
    utility_scores: Dict[str, float] = field(default_factory=dict)
    key_features: Dict[str, Any] = field(default_factory=dict)

    compose_notes: Dict[str, Any] = field(default_factory=dict)
    validator_issues: List[str] = field(default_factory=list)
    validator_used_fallback: bool = False

    final_command: Dict[str, Any] = field(default_factory=dict)
    debug_tags: List[str] = field(default_factory=list)


class DecisionTracer:
    """
    Сборщик и эмиттер decision trace.

    Задачи:
    - собрать понятную запись решения на тик;
    - отдать ее в logger;
    - при желании хранить короткую историю последних записей.
    """

    def __init__(
        self,
        logger: BotLogger,
        *,
        keep_last_n: int = 50,
        enabled: bool = True,
    ) -> None:
        self._logger = logger
        self._enabled = enabled
        self._keep_last_n = keep_last_n
        self._buffer: List[DecisionTraceEntry] = []

    def record(
        self,
        *,
        ctx: TickDecisionContext,
        decision: TickDecisionResult,
        compose_result: ActionComposeResult,
        validation_result: ValidationResult,
    ) -> Optional[DecisionTraceEntry]:
        if not self._enabled:
            return None

        entry = DecisionTraceEntry(
            tick=ctx.tick,
            round_index=ctx.round_index,
            map_id=ctx.map_id,
            selected_mode=decision.selected_mode.value,
            used_reactive_override=decision.used_reactive_override,
            reactive_reason=decision.reactive_reason,
            proposal_intent=decision.proposal.intent,
            utility_scores=self._extract_utility_scores(decision),
            key_features=self._extract_key_features(ctx.features),
            compose_notes=dict(compose_result.notes),
            validator_issues=list(validation_result.issues),
            validator_used_fallback=validation_result.used_fallback,
            final_command=validation_result.command.to_dict(),
            debug_tags=list(validation_result.command.debug_tags),
        )

        self._append(entry)
        self._emit(entry)
        return entry

    def last_entries(self) -> List[DecisionTraceEntry]:
        return list(self._buffer)

    def clear(self) -> None:
        self._buffer.clear()

    def _append(self, entry: DecisionTraceEntry) -> None:
        self._buffer.append(entry)
        if len(self._buffer) > self._keep_last_n:
            overflow = len(self._buffer) - self._keep_last_n
            del self._buffer[:overflow]

    def _emit(self, entry: DecisionTraceEntry) -> None:
        self._logger.debug(
            "decision_trace",
            "Decision trace entry recorded",
            tick=entry.tick,
            round_index=entry.round_index,
            map_id=entry.map_id,
            selected_mode=entry.selected_mode,
            reactive=entry.used_reactive_override,
            reactive_reason=entry.reactive_reason,
            proposal_intent=entry.proposal_intent,
            utility_scores=entry.utility_scores,
            key_features=entry.key_features,
            compose_notes=entry.compose_notes,
            validator_issues=entry.validator_issues,
            validator_used_fallback=entry.validator_used_fallback,
            final_command=entry.final_command,
            debug_tags=entry.debug_tags,
        )

    def _extract_utility_scores(
        self,
        decision: TickDecisionResult,
    ) -> Dict[str, float]:
        result: Dict[str, float] = {}
        for mode, score_obj in decision.utility_scores.items():
            result[mode.value] = float(score_obj.score)
        return result

    def _extract_key_features(
        self,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Берем только ключевые decision-driving features,
        чтобы не раздувать trace всем подряд.
        """
        important_keys = [
            "dist_enemy",
            "dist_nearest_weapon",
            "dist_nearest_cover",
            "los_enemy",
            "enemy_has_los_to_us",
            "self_has_weapon",
            "enemy_has_weapon",
            "self_weapon_type",
            "enemy_weapon_type",
            "self_ammo_ratio",
            "incoming_bullet_risk",
            "melee_threat",
            "cover_advantage",
            "resource_advantage",
            "timeout_advantage",
            "guaranteed_shot_window",
            "kick_confirm_window",
            "enemy_stunned_window",
            "free_pickup_window",
            "mailbox_safe_hit_window",
            "should_kite",
            "should_commit",
            "should_disengage",
            "should_force_mailbox",
            "should_play_timeout",
        ]

        extracted: Dict[str, Any] = {}
        for key in important_keys:
            if key in features:
                extracted[key] = self._sanitize_feature_value(features[key])

        return extracted

    def _sanitize_feature_value(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(k): self._sanitize_feature_value(v) for k, v in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [self._sanitize_feature_value(v) for v in value]
        return repr(value)
