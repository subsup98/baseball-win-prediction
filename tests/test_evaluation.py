import numpy as np
import pandas as pd

from mlb_winprob.evaluation import evaluate_probabilities, model_selection_rules
from mlb_winprob.experiments import select_feature_columns


def test_evaluate_probabilities_includes_confidence_bands():
    metrics = evaluate_probabilities(
        np.array([1, 0, 1, 0]),
        np.array([0.8, 0.3, 0.55, 0.45]),
    )

    assert metrics["accuracy"] == 1.0
    assert metrics["coverage_conf_55"] == 1.0
    assert metrics["accuracy_conf_55"] == 1.0


def test_select_feature_columns_excludes_all_null_numeric_columns():
    features = pd.DataFrame(
        {
            "game_id": ["1", "2"],
            "home_team_win": [1, 0],
            "usable_feature": [0.1, 0.2],
            "all_null_feature": [np.nan, np.nan],
        }
    )

    assert select_feature_columns(features) == ["usable_feature"]


def test_model_selection_rules_choose_overall_and_confidence_band_models():
    metrics = pd.DataFrame(
        [
            {
                "holdout_season": 2024,
                "model_name": "logistic",
                "log_loss": 0.68,
                "brier_score": 0.24,
                "accuracy_conf_60": 0.61,
                "coverage_conf_60": 0.30,
            },
            {
                "holdout_season": 2024,
                "model_name": "random_forest",
                "log_loss": 0.66,
                "brier_score": 0.23,
                "accuracy_conf_60": 0.58,
                "coverage_conf_60": 0.40,
            },
        ]
    )

    rules = model_selection_rules(metrics, confidence_thresholds=(0.60,), min_coverage=0.10)

    assert rules.loc[rules["rule_name"] == "overall_log_loss", "selected_model"].iloc[0] == "random_forest"
    assert rules.loc[rules["rule_name"] == "confidence_60", "selected_model"].iloc[0] == "logistic"
