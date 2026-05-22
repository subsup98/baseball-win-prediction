import importlib.util

import pandas as pd

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
