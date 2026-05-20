"""Model registry for comparable win-probability experiments."""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, StackingClassifier
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
    if normalized == "catboost":
        try:
            from catboost import CatBoostClassifier
        except ImportError as exc:
            raise ModelUnavailableError("catboost is not installed. Install with .[boosters].") from exc
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                (
                    "model",
                    CatBoostClassifier(
                        iterations=600,
                        learning_rate=0.03,
                        depth=5,
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
        "hybrid_stacking",
    ]
