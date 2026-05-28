"""Training and model comparison workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import (
    GradientBoostingRegressor,
    HistGradientBoostingRegressor,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

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


@dataclass
class ExpectedRunsResult:
    metrics: pd.DataFrame
    synthetic_ou_metrics: pd.DataFrame
    fitted_models: dict[str, Any]
    feature_columns: list[str]


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


def run_oof_win_predictions(
    features: pd.DataFrame,
    *,
    model_names: list[str],
    holdout_seasons: list[int],
    prediction_mode: str | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Generate season-holdout out-of-fold win probabilities by model."""

    frame = features.copy()
    if prediction_mode is not None and "prediction_mode" in frame.columns:
        frame = frame[frame["prediction_mode"] == prediction_mode].copy()
    if TARGET_COLUMN not in frame.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")

    rows: list[pd.DataFrame] = []
    identity_columns = [
        column
        for column in [
            "game_id",
            "game_date",
            "season",
            "home_team",
            "away_team",
            "home_score",
            "away_score",
            TARGET_COLUMN,
        ]
        if column in frame.columns
    ]
    for holdout_season in holdout_seasons:
        train, test = season_holdout_split(frame, holdout_season=holdout_season)
        feature_columns = select_feature_columns(train)
        if not feature_columns:
            continue
        x_train = train[feature_columns]
        y_train = train[TARGET_COLUMN].astype(int)
        x_test = test[feature_columns]

        for model_name in model_names:
            if model_name.lower() == "elo":
                model = EloRatingModel()
                model.fit(train)
                probabilities = model.predict_proba_sequential(test)
            else:
                try:
                    model = make_classifier(model_name, random_state=random_state)
                    model.fit(x_train, y_train)
                    probabilities = model.predict_proba(x_test)[:, 1]
                except ModelUnavailableError:
                    continue

            output = test[identity_columns].copy()
            output.insert(0, "holdout_season", holdout_season)
            output.insert(1, "model_name", model_name)
            output["home_win_probability"] = probabilities
            output["away_win_probability"] = 1.0 - output["home_win_probability"]
            if {"home_team", "away_team"}.issubset(output.columns):
                output["raw_win_pick"] = np.where(
                    output["home_win_probability"] >= 0.5,
                    output["home_team"].astype(str),
                    output["away_team"].astype(str),
                )
                output["win_confidence"] = np.maximum(output["home_win_probability"], output["away_win_probability"])
            if {TARGET_COLUMN, "home_team", "away_team"}.issubset(output.columns):
                output["actual_winner"] = np.where(
                    output[TARGET_COLUMN].astype(int).eq(1),
                    output["home_team"].astype(str),
                    output["away_team"].astype(str),
                )
            rows.append(output)

    if not rows:
        return pd.DataFrame()
    return pd.concat(rows, ignore_index=True).sort_values(["holdout_season", "game_date", "game_id", "model_name"]).reset_index(drop=True)


def make_regressor(name: str, *, random_state: int = 42) -> Any:
    normalized = name.lower()
    if normalized == "ridge":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", Ridge(alpha=1.0, random_state=random_state)),
            ]
        )
    if normalized == "random_forest_regressor":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=300,
                        min_samples_leaf=8,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if normalized == "gradient_boosting_regressor":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    GradientBoostingRegressor(
                        n_estimators=300,
                        learning_rate=0.05,
                        max_depth=3,
                        min_samples_leaf=8,
                        subsample=0.85,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "hist_gradient_boosting_regressor":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        max_iter=400,
                        learning_rate=0.05,
                        max_leaf_nodes=31,
                        l2_regularization=0.1,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "lightgbm_regressor":
        try:
            from lightgbm import LGBMRegressor
        except ImportError as exc:
            raise ModelUnavailableError("lightgbm is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    LGBMRegressor(
                        n_estimators=600,
                        learning_rate=0.03,
                        num_leaves=31,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        random_state=random_state,
                        verbosity=-1,
                    ),
                ),
            ]
        )
    if normalized == "xgboost_regressor":
        try:
            from xgboost import XGBRegressor
        except ImportError as exc:
            raise ModelUnavailableError("xgboost is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBRegressor(
                        n_estimators=600,
                        learning_rate=0.03,
                        max_depth=4,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "catboost_regressor":
        try:
            from catboost import CatBoostRegressor
        except ImportError as exc:
            raise ModelUnavailableError("catboost is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    CatBoostRegressor(
                        iterations=600,
                        learning_rate=0.03,
                        depth=5,
                        l2_leaf_reg=3.0,
                        loss_function="RMSE",
                        random_seed=random_state,
                        verbose=False,
                    ),
                ),
            ]
        )
    raise ValueError(f"Unknown regressor name: {name}")


def run_expected_runs_experiments(
    features: pd.DataFrame,
    *,
    model_names: list[str] | None = None,
    holdout_season: int | None = None,
    prediction_mode: str | None = None,
    synthetic_total_lines: list[float] | None = None,
    random_state: int = 42,
) -> ExpectedRunsResult:
    frame = features.copy()
    if prediction_mode is not None and "prediction_mode" in frame.columns:
        frame = frame[frame["prediction_mode"] == prediction_mode].copy()
    for target in ["home_score", "away_score"]:
        if target not in frame.columns:
            raise ValueError(f"features must include {target}")

    train, test = season_holdout_split(frame, holdout_season=holdout_season)
    feature_columns = select_feature_columns(train)
    feature_columns = [column for column in feature_columns if column not in {"home_score", "away_score"}]
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")

    rows: list[dict[str, float | str]] = []
    ou_rows: list[dict[str, float | str]] = []
    fitted_models: dict[str, Any] = {}
    x_train = train[feature_columns]
    x_test = test[feature_columns]
    y_home = test["home_score"].astype(float)
    y_away = test["away_score"].astype(float)
    total_lines = synthetic_total_lines if synthetic_total_lines is not None else [6.5, 7.5, 8.5, 9.5, 10.5]

    for model_name in model_names or ["ridge", "random_forest_regressor"]:
        home_model = make_regressor(model_name, random_state=random_state)
        away_model = make_regressor(model_name, random_state=random_state + 1)
        home_model.fit(x_train, train["home_score"].astype(float))
        away_model.fit(x_train, train["away_score"].astype(float))
        pred_home = np.clip(home_model.predict(x_test), 0, None)
        pred_away = np.clip(away_model.predict(x_test), 0, None)
        pred_total = pred_home + pred_away
        actual_total = y_home.to_numpy(dtype=float) + y_away.to_numpy(dtype=float)
        total_abs_error = np.abs(pred_total - actual_total)
        rows.append(
            {
                "model_name": model_name,
                "home_mae": float(mean_absolute_error(y_home, pred_home)),
                "away_mae": float(mean_absolute_error(y_away, pred_away)),
                "total_mae": float(mean_absolute_error(actual_total, pred_total)),
                "total_rmse": float(mean_squared_error(actual_total, pred_total) ** 0.5),
                "total_within_1": float(np.mean(total_abs_error <= 1.0)),
                "total_within_2": float(np.mean(total_abs_error <= 2.0)),
                "total_within_3": float(np.mean(total_abs_error <= 3.0)),
                "run_diff_mae": float(mean_absolute_error(y_home - y_away, pred_home - pred_away)),
                "n_games": float(len(test)),
            }
        )
        for total_line in total_lines:
            predicted_over = pred_total > total_line
            actual_over = actual_total > total_line
            margins = pred_total - total_line
            ou_rows.append(
                {
                    "model_name": model_name,
                    "total_line": float(total_line),
                    "ou_accuracy": float(np.mean(predicted_over == actual_over)),
                    "over_pick_rate": float(np.mean(predicted_over)),
                    "actual_over_rate": float(np.mean(actual_over)),
                    "mean_abs_margin": float(np.mean(np.abs(margins))),
                    "pass_rate_0_5": float(np.mean(np.abs(margins) <= 0.5)),
                    "lean_or_strong_rate_0_5": float(np.mean(np.abs(margins) > 0.5)),
                    "strong_rate_1_5": float(np.mean(np.abs(margins) > 1.5)),
                    "n_games": float(len(test)),
                }
            )
        fitted_models[f"{model_name}_home"] = home_model
        fitted_models[f"{model_name}_away"] = away_model

    return ExpectedRunsResult(
        metrics=pd.DataFrame(rows).sort_values(["total_mae", "total_rmse"]).reset_index(drop=True),
        synthetic_ou_metrics=pd.DataFrame(ou_rows).sort_values(["model_name", "total_line"]).reset_index(drop=True),
        fitted_models=fitted_models,
        feature_columns=feature_columns,
    )


def add_expected_runs_prediction_features(
    features: pd.DataFrame,
    *,
    holdout_seasons: list[int],
    model_name: str = "ridge",
    prediction_mode: str | None = None,
    random_state: int = 42,
) -> pd.DataFrame:
    """Add holdout-safe expected-run predictions for each requested season.

    Each holdout season is predicted by regressors trained only on earlier
    seasons, matching the season-holdout evaluation contract.
    """

    frame = features.copy()
    if prediction_mode is not None and "prediction_mode" in frame.columns:
        mode_mask = frame["prediction_mode"] == prediction_mode
    else:
        mode_mask = pd.Series(True, index=frame.index)
    for target in ["home_score", "away_score", "season"]:
        if target not in frame.columns:
            raise ValueError(f"features must include {target}")

    output_columns = [
        "expected_home_runs",
        "expected_away_runs",
        "expected_total_runs",
        "expected_run_diff",
    ]
    for column in output_columns:
        frame[column] = np.nan

    for season in holdout_seasons:
        train = frame[mode_mask & (frame["season"] < season)].copy()
        test = frame[mode_mask & (frame["season"] == season)].copy()
        if train.empty or test.empty:
            continue
        feature_columns = select_feature_columns(train)
        feature_columns = [column for column in feature_columns if column not in {"home_score", "away_score", *output_columns}]
        if not feature_columns:
            continue

        home_model = make_regressor(model_name, random_state=random_state)
        away_model = make_regressor(model_name, random_state=random_state + 1)
        home_model.fit(train[feature_columns], train["home_score"].astype(float))
        away_model.fit(train[feature_columns], train["away_score"].astype(float))
        pred_home = np.clip(home_model.predict(test[feature_columns]), 0, None)
        pred_away = np.clip(away_model.predict(test[feature_columns]), 0, None)
        frame.loc[test.index, "expected_home_runs"] = pred_home
        frame.loc[test.index, "expected_away_runs"] = pred_away
        frame.loc[test.index, "expected_total_runs"] = pred_home + pred_away
        frame.loc[test.index, "expected_run_diff"] = pred_home - pred_away

    return frame
