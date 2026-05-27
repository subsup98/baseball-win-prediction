import importlib.util

import pandas as pd

from mlb_winprob.experiments import select_feature_columns
from mlb_winprob.models import make_classifier


def test_sklearn_model_test_candidates_predict_probabilities():
    x = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 0.2, 0.8, -0.1, 1.2],
            "feature_b": [1.0, 0.0, 0.7, 0.3, 1.1, -0.2],
        }
    )
    y = [0, 1, 0, 1, 0, 1]

    for name in ["logistic_l1", "random_forest_shallow", "extra_trees", "hist_gradient_boosting"]:
        model = make_classifier(name)
        model.fit(x, y)
        probabilities = model.predict_proba(x)
        assert probabilities.shape == (6, 2)


def test_catboost_tuning_candidates_predict_probabilities_when_available():
    if importlib.util.find_spec("catboost") is None:
        return
    x = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 0.2, 0.8, -0.1, 1.2],
            "feature_b": [1.0, 0.0, 0.7, 0.3, 1.1, -0.2],
        }
    )
    y = [0, 1, 0, 1, 0, 1]

    for name in ["catboost_shallow", "catboost_l2", "catboost_lr02"]:
        model = make_classifier(name)
        model.fit(x, y)
        probabilities = model.predict_proba(x)
        assert probabilities.shape == (6, 2)


def test_voting_candidates_predict_probabilities_when_boosters_available():
    required = ["catboost", "lightgbm", "xgboost"]
    if any(importlib.util.find_spec(name) is None for name in required):
        return
    x = pd.DataFrame(
        {
            "feature_a": [0.0, 1.0, 0.2, 0.8, -0.1, 1.2, 0.3, 0.9],
            "feature_b": [1.0, 0.0, 0.7, 0.3, 1.1, -0.2, 0.5, 0.4],
        }
    )
    y = [0, 1, 0, 1, 0, 1, 0, 1]

    for name in ["soft_voting", "booster_voting"]:
        model = make_classifier(name)
        model.fit(x, y)
        probabilities = model.predict_proba(x)
        assert probabilities.shape == (8, 2)


def test_select_feature_columns_excludes_target_identifiers_and_all_nulls():
    features = pd.DataFrame(
        {
            "game_id": ["g1", "g2"],
            "season": [2025, 2025],
            "home_team_win": [1, 0],
            "numeric_signal": [0.1, 0.2],
            "all_null": [pd.NA, pd.NA],
        }
    )

    assert select_feature_columns(features) == ["numeric_signal"]
