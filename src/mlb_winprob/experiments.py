"""Training and model comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from mlb_winprob.constants import NON_FEATURE_COLUMNS, TARGET_COLUMN
from mlb_winprob.evaluation import calibration_table, evaluate_probabilities, season_holdout_split
from mlb_winprob.models import EloRatingModel, ModelUnavailableError, default_model_names, make_classifier


@dataclass
class ExperimentResult:
    metrics: pd.DataFrame
    calibration: dict[str, pd.DataFrame]
    fitted_models: dict[str, Any]
    feature_columns: list[str]

    @property
    def best_model_name(self) -> str:
        if self.metrics.empty:
            raise ValueError("No successful model runs.")
        return str(self.metrics.sort_values(["log_loss", "brier_score"]).iloc[0]["model_name"])


def select_feature_columns(features: pd.DataFrame) -> list[str]:
    candidates = features.select_dtypes(include=["number", "bool"]).columns.tolist()
    return [
        column
        for column in candidates
        if column not in NON_FEATURE_COLUMNS and features[column].notna().any()
    ]


def run_model_experiments(
    features: pd.DataFrame,
    *,
    model_names: list[str] | None = None,
    holdout_season: int | None = None,
    prediction_mode: str | None = None,
    random_state: int = 42,
) -> ExperimentResult:
    frame = features.copy()
    if prediction_mode is not None and "prediction_mode" in frame.columns:
        frame = frame[frame["prediction_mode"] == prediction_mode].copy()
    if TARGET_COLUMN not in frame.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")

    train, test = season_holdout_split(frame, holdout_season=holdout_season)
    feature_columns = select_feature_columns(train)
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")

    x_train = train[feature_columns]
    y_train = train[TARGET_COLUMN].astype(int)
    x_test = test[feature_columns]
    y_test = test[TARGET_COLUMN].astype(int)

    rows: list[dict[str, float | str]] = []
    calibration: dict[str, pd.DataFrame] = {}
    fitted_models: dict[str, Any] = {}

    for model_name in model_names or default_model_names():
        if model_name.lower() == "elo":
            elo = EloRatingModel()
            elo.fit(train)
            probability = elo.predict_proba_sequential(test)
            metrics = evaluate_probabilities(y_test, probability)
            rows.append({"model_name": model_name, **metrics})
            calibration[model_name] = calibration_table(y_test, probability)
            fitted_models[model_name] = elo
            continue

        try:
            estimator = make_classifier(model_name, random_state=random_state)
            estimator.fit(x_train, y_train)
            probability = estimator.predict_proba(x_test)[:, 1]
        except ModelUnavailableError:
            continue
        metrics = evaluate_probabilities(y_test, probability)
        rows.append({"model_name": model_name, **metrics})
        calibration[model_name] = calibration_table(y_test, probability)
        fitted_models[model_name] = estimator

    return ExperimentResult(
        metrics=pd.DataFrame(rows).sort_values(["log_loss", "brier_score"]).reset_index(drop=True) if rows else pd.DataFrame(),
        calibration=calibration,
        fitted_models=fitted_models,
        feature_columns=feature_columns,
    )
