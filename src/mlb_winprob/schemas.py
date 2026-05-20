"""Small typed objects used across the pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FeatureBuildConfig:
    """Configuration for building one game-level feature table."""

    prediction_mode: str = "confirmed_lineup"
    fip_constant: float = 3.1
    home_field_advantage: float = 1.0
    lineup_order_weights: dict[int, float] = field(
        default_factory=lambda: {
            1: 0.12,
            2: 0.12,
            3: 0.13,
            4: 0.13,
            5: 0.12,
            6: 0.11,
            7: 0.10,
            8: 0.09,
            9: 0.08,
        }
    )


@dataclass(frozen=True)
class PredictionResult:
    """Public prediction response."""

    home_win_probability: float
    away_win_probability: float
    model_name: str
    prediction_mode: str
    key_reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "home_win_probability": self.home_win_probability,
            "away_win_probability": self.away_win_probability,
            "model_name": self.model_name,
            "prediction_mode": self.prediction_mode,
            "key_reasons": self.key_reasons,
        }
