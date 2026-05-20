"""Prediction response helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd

from mlb_winprob.schemas import PredictionResult


def build_prediction_result(
    home_win_probability: float,
    *,
    model_name: str,
    prediction_mode: str,
    key_reasons: list[str] | None = None,
) -> PredictionResult:
    probability = float(np.clip(home_win_probability, 0.0, 1.0))
    return PredictionResult(
        home_win_probability=probability,
        away_win_probability=1.0 - probability,
        model_name=model_name,
        prediction_mode=prediction_mode,
        key_reasons=key_reasons or [],
    )


def simple_key_reasons(
    row: pd.Series,
    *,
    max_reasons: int = 4,
) -> list[str]:
    candidates = [
        ("sp_fip_diff", "선발투수 FIP 차이가 홈팀에 유리합니다.", "선발투수 FIP 차이가 원정팀에 유리합니다."),
        ("lineup_woba_diff", "라인업 wOBA 차이가 홈팀에 유리합니다.", "라인업 wOBA 차이가 원정팀에 유리합니다."),
        ("bullpen_fatigue_diff", "불펜 피로도 차이가 홈팀에 유리합니다.", "불펜 피로도 차이가 원정팀에 유리합니다."),
        ("team_woba_diff", "팀 공격력 wOBA 차이가 홈팀에 유리합니다.", "팀 공격력 wOBA 차이가 원정팀에 유리합니다."),
    ]
    scored: list[tuple[float, str]] = []
    for column, positive_reason, negative_reason in candidates:
        value = row.get(column)
        if pd.isna(value):
            continue
        reason = positive_reason if float(value) >= 0 else negative_reason
        scored.append((abs(float(value)), reason))
    scored.sort(reverse=True)
    return [reason for _, reason in scored[:max_reasons]]
