import numpy as np
import pandas as pd

from mlb_winprob.evaluation import evaluate_probabilities
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
