import numpy as np
import pandas as pd
import pytest

from mlb_winprob.evaluation import (
    apply_model_agreement_pick_rules,
    apply_ou_pick_rules,
    apply_win_pick_rules,
    evaluate_probabilities,
    model_selection_rules,
    summarize_ou_pick_rules,
    summarize_win_pick_rules,
)
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


def test_apply_win_pick_rules_marks_pass_lean_and_strong():
    predictions = pd.DataFrame(
        {
            "home_team": ["A", "B", "C"],
            "away_team": ["X", "Y", "Z"],
            "home_win_probability": [0.51, 0.56, 0.62],
            "actual_winner": ["A", "Y", "C"],
        }
    )

    ruled = apply_win_pick_rules(predictions, lean_threshold=0.55, strong_threshold=0.60)

    assert ruled["win_pick_rule"].tolist() == ["pass", "lean", "strong"]
    assert ruled["rule_win_pick"].tolist() == ["", "B", "C"]
    assert pd.isna(ruled.loc[0, "rule_win_correct"])
    assert ruled.loc[1, "rule_win_correct"] == np.False_
    assert ruled.loc[2, "rule_win_correct"] == np.True_


def test_apply_win_pick_rules_does_not_score_missing_actual_winner():
    predictions = pd.DataFrame(
        {
            "home_team": ["A", "B"],
            "away_team": ["X", "Y"],
            "home_win_probability": [0.61, 0.39],
            "actual_winner": ["", np.nan],
        }
    )

    ruled = apply_win_pick_rules(predictions, lean_threshold=0.55, strong_threshold=0.60)

    assert ruled["win_pick_rule"].tolist() == ["strong", "strong"]
    assert ruled["rule_win_correct"].isna().all()


def test_summarize_win_pick_rules_reports_actionable_accuracy():
    predictions = pd.DataFrame(
        {
            "home_team": ["A", "B", "C", "D"],
            "away_team": ["X", "Y", "Z", "W"],
            "home_win_probability": [0.51, 0.56, 0.62, 0.42],
            "actual_winner": ["A", "Y", "C", "W"],
        }
    )
    ruled = apply_win_pick_rules(predictions, lean_threshold=0.55, strong_threshold=0.60)

    summary = summarize_win_pick_rules(ruled)

    actionable = summary[summary["rule"] == "actionable"].iloc[0]
    assert actionable["picks"] == 3
    assert actionable["hits"] == 2
    assert actionable["accuracy"] == pytest.approx(2 / 3)


def test_apply_ou_pick_rules_marks_pass_lean_and_strong():
    predictions = pd.DataFrame(
        {
            "pred_total": [8.3, 7.9, 10.2],
            "total_line": [8.5, 8.5, 8.5],
            "actual_total": [8, 9, 11],
        }
    )
    ruled = apply_ou_pick_rules(predictions, lean_margin=0.5, strong_margin=1.5)

    assert ruled["ou_pick_rule"].tolist() == ["pass", "lean", "strong"]
    assert ruled["rule_ou_pick"].tolist() == ["", "under", "over"]
    assert pd.isna(ruled.loc[0, "rule_ou_correct"])  # pass is not scored
    assert ruled.loc[1, "rule_ou_correct"] == np.False_  # under pick, actual 9 > 8.5 -> over, wrong
    assert ruled.loc[2, "rule_ou_correct"] == np.True_  # strong over, actual 11 > 8.5 -> over correct


def test_apply_ou_pick_rules_scores_against_actual_total():
    predictions = pd.DataFrame(
        {
            "pred_total": [7.5],  # margin -1.0 -> under (lean)
            "total_line": [8.5],
            "actual_total": [10],  # actual over -> under pick is wrong
        }
    )
    ruled = apply_ou_pick_rules(predictions, lean_margin=0.5, strong_margin=1.5)
    assert ruled.loc[0, "ou_pick_rule"] == "lean"
    assert ruled.loc[0, "rule_ou_pick"] == "under"
    assert ruled.loc[0, "rule_ou_correct"] == np.False_


def test_summarize_ou_pick_rules_reports_actionable_accuracy():
    predictions = pd.DataFrame(
        {
            "pred_total": [8.4, 7.9, 10.2, 8.55],
            "total_line": [8.5, 8.5, 8.5, 8.5],
            "actual_total": [8, 8, 11, 9],
        }
    )
    ruled = apply_ou_pick_rules(predictions, lean_margin=0.5, strong_margin=1.5)
    summary = summarize_ou_pick_rules(ruled)

    actionable = summary[summary["rule"] == "actionable"].iloc[0]
    # rows: 0 pass, 1 lean(under, actual 8 -> under correct), 2 strong(over, actual 11 -> over correct), 3 pass
    assert actionable["picks"] == 2
    assert actionable["hits"] == 2
    assert actionable["accuracy"] == pytest.approx(1.0)


def test_apply_model_agreement_pick_rules_requires_challenger_pick_match():
    predictions = pd.DataFrame(
        {
            "holdout_season": [2024, 2024, 2024, 2024],
            "game_id": ["g1", "g1", "g2", "g2"],
            "model_name": ["main", "challenger", "main", "challenger"],
            "home_team": ["A", "A", "B", "B"],
            "away_team": ["X", "X", "Y", "Y"],
            "home_win_probability": [0.61, 0.58, 0.62, 0.42],
            "actual_winner": ["A", "A", "B", "B"],
        }
    )

    ruled = apply_model_agreement_pick_rules(
        predictions,
        primary_model="main",
        challenger_models=["challenger"],
        lean_threshold=0.55,
        strong_threshold=0.60,
    )

    assert ruled.sort_values("game_id")["win_pick_rule"].tolist() == ["strong", "pass"]
    summary = summarize_win_pick_rules(ruled)
    actionable = summary[summary["rule"] == "actionable"].iloc[0]
    assert actionable["picks"] == 1
    assert actionable["hits"] == 1
