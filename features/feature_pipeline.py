from __future__ import annotations

from dataclasses import dataclass

from features.basic_features import DerivedFeatures, extract_basic_features
from state.world_state import WorldState


@dataclass(slots=True)
class FeatureBundle:
    basic: DerivedFeatures


class FeaturePipeline:
    """
    Единая точка расчета всех derived features.

    Сейчас содержит только basic-features слой.
    Позже сюда можно добавить:
    - geometry features;
    - opponent model features;
    - timeout/control features;
    - map-specific features.
    """

    def extract(self, world_state: WorldState) -> FeatureBundle:
        basic = extract_basic_features(world_state)

        return FeatureBundle(
            basic=basic,
        )
