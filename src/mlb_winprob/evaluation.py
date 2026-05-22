"""Model evaluation utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from mlb_winprob.constants import CONFIDENCE_THRESHOLDS, TARGET_COLUMN


def evaluate_probabilities(
    y_true: pd.Series | np.ndarray,
    home_win_probability: pd.Series | np.ndarray,
    *,
    confidence_thresholds: tuple[float, ...] = CONFIDENCE_THRESHOLDS,
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=int)
    probabilities = np.clip(np.asarray(home_win_probability, dtype=float), 1e-6, 1 - 1e-6)
    predictions = (probabilities >= 0.5).astype(int)
    metrics: dict[str, float] = {
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "accuracy": float(accuracy_score(y, predictions)),
        "n_games": float(len(y)),
    }

    confidence = np.maximum(probabilities, 1 - probabilities)
    for threshold in confidence_thresholds:
        mask = confidence >= threshold
        key = f"accuracy_conf_{int(threshold * 100)}"
        coverage_key = f"coverage_conf_{int(threshold * 100)}"
        metrics[key] = float(accuracy_score(y[mask], predictions[mask])) if mask.any() else np.nan
        metrics[coverage_key] = float(mask.mean())
    return metrics


def calibration_table(
    y_true: pd.Series | np.ndarray,
    home_win_probability: pd.Series | np.ndarray,
    *,
    bins: int = 10,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "y_true": np.asarray(y_true, dtype=int),
            "probability": np.asarray(home_win_probability, dtype=float),
        }
    )
    frame["bin"] = pd.cut(frame["probability"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    table = (
        frame.groupby("bin", observed=False)
        .agg(
            n_games=("y_true", "size"),
            predicted_home_win_rate=("probability", "mean"),
            actual_home_win_rate=("y_true", "mean"),
        )
        .reset_index()
    )
    table["calibration_error"] = table["predicted_home_win_rate"] - table["actual_home_win_rate"]
    return table


def model_selection_rules(
    metrics: pd.DataFrame,
    *,
    confidence_thresholds: tuple[float, ...] = CONFIDENCE_THRESHOLDS,
    min_coverage: float = 0.10,
) -> pd.DataFrame:
    """Choose simple per-holdout model rules from existing metrics.

    The output is intentionally rule-based and auditable: one overall log-loss
    winner plus optional confidence-band winners when coverage is high enough.
    """

    if metrics.empty:
        return pd.DataFrame()
    required = {"holdout_season", "model_name", "log_loss", "brier_score"}
    missing = required - set(metrics.columns)
    if missing:
        raise ValueError(f"metrics is missing required columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for season, group in metrics.groupby("holdout_season", sort=True):
        overall = group.sort_values(["log_loss", "brier_score", "model_name"]).iloc[0]
        rows.append(
            {
                "holdout_season": season,
                "rule_name": "overall_log_loss",
                "selected_model": overall["model_name"],
                "selection_metric": "log_loss",
                "selection_value": float(overall["log_loss"]),
                "coverage": 1.0,
            }
        )
        for threshold in confidence_thresholds:
            suffix = int(threshold * 100)
            accuracy_column = f"accuracy_conf_{suffix}"
            coverage_column = f"coverage_conf_{suffix}"
            if accuracy_column not in group.columns or coverage_column not in group.columns:
                continue
            eligible = group[group[coverage_column].fillna(0) >= min_coverage].copy()
            eligible = eligible.dropna(subset=[accuracy_column])
            if eligible.empty:
                continue
            selected = eligible.sort_values(
                [accuracy_column, coverage_column, "log_loss", "model_name"],
                ascending=[False, False, True, True],
            ).iloc[0]
            rows.append(
                {
                    "holdout_season": season,
                    "rule_name": f"confidence_{suffix}",
                    "selected_model": selected["model_name"],
                    "selection_metric": accuracy_column,
                    "selection_value": float(selected[accuracy_column]),
                    "coverage": float(selected[coverage_column]),
                }
            )
    return pd.DataFrame(rows)


def temporal_train_test_split(
    features: pd.DataFrame,
    *,
    test_fraction: float = 0.2,
    date_column: str = "game_date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if TARGET_COLUMN not in features.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")
    frame = features.dropna(subset=[TARGET_COLUMN]).copy()
    frame[date_column] = pd.to_datetime(frame[date_column])
    frame = frame.sort_values([date_column, "game_id"]).reset_index(drop=True)
    split_index = max(1, int(len(frame) * (1 - test_fraction)))
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()


def season_holdout_split(
    features: pd.DataFrame,
    *,
    holdout_season: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if TARGET_COLUMN not in features.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")
    frame = features.dropna(subset=[TARGET_COLUMN]).copy()
    if holdout_season is None:
        holdout_season = int(frame["season"].max())
    train = frame[frame["season"] < holdout_season].copy()
    test = frame[frame["season"] == holdout_season].copy()
    if train.empty or test.empty:
        return temporal_train_test_split(frame)
    return train, test
