"""Model registry for comparable win-probability experiments."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import (
    ExtraTreesClassifier,
    HistGradientBoostingClassifier,
    RandomForestClassifier,
    StackingClassifier,
    VotingClassifier,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class ModelUnavailableError(RuntimeError):
    """Raised when an optional model dependency is not installed."""


@dataclass(frozen=True)
class ModelSpec:
    name: str
    estimator: Any


class EloRatingModel:
    """Simple chronological Elo baseline for home-team win probability."""

    def __init__(
        self,
        *,
        initial_rating: float = 1500.0,
        k_factor: float = 20.0,
        home_advantage_rating: float = 55.0,
        scale: float = 400.0,
    ) -> None:
        self.initial_rating = initial_rating
        self.k_factor = k_factor
        self.home_advantage_rating = home_advantage_rating
        self.scale = scale
        self.ratings: defaultdict[str, float] = defaultdict(lambda: self.initial_rating)

    def fit(self, games: pd.DataFrame) -> "EloRatingModel":
        frame = self._sorted_games(games)
        for _, row in frame.iterrows():
            probability = self._home_probability(row["home_team"], row["away_team"])
            self._update(row["home_team"], row["away_team"], float(row["home_team_win"]), probability)
        return self

    def predict_proba_sequential(self, games: pd.DataFrame) -> np.ndarray:
        frame = self._sorted_games(games)
        probabilities: list[float] = []
        for _, row in frame.iterrows():
            probability = self._home_probability(row["home_team"], row["away_team"])
            probabilities.append(probability)
            if "home_team_win" in row and pd.notna(row["home_team_win"]):
                self._update(row["home_team"], row["away_team"], float(row["home_team_win"]), probability)
        return np.asarray(probabilities, dtype=float)

    def _home_probability(self, home_team: str, away_team: str) -> float:
        home_rating = self.ratings[str(home_team)] + self.home_advantage_rating
        away_rating = self.ratings[str(away_team)]
        return float(1.0 / (1.0 + 10.0 ** ((away_rating - home_rating) / self.scale)))

    def _update(self, home_team: str, away_team: str, actual_home_win: float, expected_home_win: float) -> None:
        delta = self.k_factor * (actual_home_win - expected_home_win)
        self.ratings[str(home_team)] += delta
        self.ratings[str(away_team)] -= delta

    @staticmethod
    def _sorted_games(games: pd.DataFrame) -> pd.DataFrame:
        frame = games.copy()
        frame["game_date"] = pd.to_datetime(frame["game_date"])
        return frame.sort_values(["game_date", "game_id"]).reset_index(drop=True)


def make_classifier(name: str, *, random_state: int = 42) -> Any:
    normalized = name.lower()
    if normalized == "logistic":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(max_iter=2000, random_state=random_state)),
            ]
        )
    if normalized == "logistic_l1":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    LogisticRegression(
                        C=0.5,
                        max_iter=5000,
                        penalty="l1",
                        l1_ratio=1.0,
                        solver="saga",
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "logistic_l2_c03":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(C=0.3, max_iter=3000, random_state=random_state)),
            ]
        )
    if normalized == "logistic_l2_c3":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("model", LogisticRegression(C=3.0, max_iter=3000, random_state=random_state)),
            ]
        )
    if normalized == "random_forest":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=400,
                        min_samples_leaf=8,
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if normalized == "random_forest_shallow":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=350,
                        max_depth=7,
                        min_samples_leaf=16,
                        max_features="sqrt",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if normalized == "random_forest_deep":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    RandomForestClassifier(
                        n_estimators=500,
                        min_samples_leaf=4,
                        max_features="sqrt",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if normalized == "extra_trees":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    ExtraTreesClassifier(
                        n_estimators=500,
                        min_samples_leaf=8,
                        max_features="sqrt",
                        random_state=random_state,
                        n_jobs=-1,
                    ),
                ),
            ]
        )
    if normalized == "hist_gradient_boosting":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    HistGradientBoostingClassifier(
                        learning_rate=0.04,
                        max_iter=250,
                        max_leaf_nodes=15,
                        l2_regularization=0.05,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "calibrated_logistic":
        return CalibratedClassifierCV(
            estimator=make_classifier("logistic_l2_c03", random_state=random_state),
            method="isotonic",
            cv=3,
        )
    if normalized == "calibrated_random_forest":
        return CalibratedClassifierCV(
            estimator=make_classifier("random_forest_shallow", random_state=random_state),
            method="sigmoid",
            cv=3,
        )
    if normalized == "mlp":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                (
                    "model",
                    MLPClassifier(
                        hidden_layer_sizes=(96, 48),
                        early_stopping=True,
                        max_iter=600,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "lightgbm":
        try:
            from lightgbm import LGBMClassifier
        except ImportError as exc:
            raise ModelUnavailableError("lightgbm is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    LGBMClassifier(
                        n_estimators=600,
                        learning_rate=0.03,
                        num_leaves=31,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise ModelUnavailableError("xgboost is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    XGBClassifier(
                        n_estimators=600,
                        learning_rate=0.03,
                        max_depth=4,
                        subsample=0.85,
                        colsample_bytree=0.85,
                        eval_metric="logloss",
                        random_state=random_state,
                    ),
                ),
            ]
        )
    if normalized in {"catboost", "catboost_shallow", "catboost_l2", "catboost_lr02"}:
        try:
            from catboost import CatBoostClassifier
        except ImportError as exc:
            raise ModelUnavailableError("catboost is not installed. Install with .[boosters].") from exc
        catboost_params = {
            "catboost": {"iterations": 600, "learning_rate": 0.03, "depth": 5, "l2_leaf_reg": 3.0},
            "catboost_shallow": {"iterations": 500, "learning_rate": 0.03, "depth": 3, "l2_leaf_reg": 6.0},
            "catboost_l2": {"iterations": 700, "learning_rate": 0.025, "depth": 4, "l2_leaf_reg": 12.0},
            "catboost_lr02": {"iterations": 800, "learning_rate": 0.02, "depth": 4, "l2_leaf_reg": 8.0},
        }[normalized]
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    CatBoostClassifier(
                        **catboost_params,
                        loss_function="Logloss",
                        random_seed=random_state,
                        verbose=False,
                    ),
                ),
            ]
        )
    if normalized == "hybrid_stacking":
        base_estimators = [
            ("logistic", make_classifier("logistic", random_state=random_state)),
            ("random_forest", make_classifier("random_forest", random_state=random_state)),
            ("mlp", make_classifier("mlp", random_state=random_state)),
        ]
        return StackingClassifier(
            estimators=base_estimators,
            final_estimator=LogisticRegression(max_iter=2000, random_state=random_state),
            stack_method="predict_proba",
            n_jobs=-1,
        )
    if normalized == "soft_voting":
        base_estimators = [
            ("logistic", make_classifier("logistic", random_state=random_state)),
            ("random_forest", make_classifier("random_forest", random_state=random_state)),
            ("random_forest_shallow", make_classifier("random_forest_shallow", random_state=random_state)),
            ("extra_trees", make_classifier("extra_trees", random_state=random_state)),
        ]
        return VotingClassifier(estimators=base_estimators, voting="soft", n_jobs=-1)
    if normalized == "booster_voting":
        base_estimators = [
            ("hist_gradient_boosting", make_classifier("hist_gradient_boosting", random_state=random_state)),
            ("lightgbm", make_classifier("lightgbm", random_state=random_state)),
            ("xgboost", make_classifier("xgboost", random_state=random_state)),
            ("catboost_shallow", make_classifier("catboost_shallow", random_state=random_state)),
        ]
        return VotingClassifier(estimators=base_estimators, voting="soft", n_jobs=-1)
    if normalized == "booster_stacking":
        base_estimators = [
            ("hist_gradient_boosting", make_classifier("hist_gradient_boosting", random_state=random_state)),
            ("lightgbm", make_classifier("lightgbm", random_state=random_state)),
            ("xgboost", make_classifier("xgboost", random_state=random_state)),
            ("catboost_shallow", make_classifier("catboost_shallow", random_state=random_state)),
        ]
        return StackingClassifier(
            estimators=base_estimators,
            final_estimator=LogisticRegression(C=0.5, max_iter=2000, random_state=random_state),
            stack_method="predict_proba",
            n_jobs=-1,
        )
    raise ValueError(f"Unknown model name: {name}")


def default_model_names() -> list[str]:
    return [
        "elo",
        "logistic",
        "random_forest",
        "mlp",
        "lightgbm",
        "xgboost",
        "catboost",
        "soft_voting",
        "booster_voting",
        "booster_stacking",
        "hybrid_stacking",
    ]
