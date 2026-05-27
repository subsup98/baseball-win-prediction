import pandas as pd

from mlb_winprob.experiments import add_expected_runs_prediction_features, run_expected_runs_experiments


def test_expected_runs_experiment_reports_run_metrics():
    features = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2023-04-01",
                "season": 2023,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_score": 5,
                "away_score": 3,
                "home_team_win": 1,
                "feature_a": 0.4,
            },
            {
                "game_id": "g2",
                "game_date": "2023-04-02",
                "season": 2023,
                "home_team": "AWY",
                "away_team": "HOM",
                "home_score": 2,
                "away_score": 4,
                "home_team_win": 0,
                "feature_a": -0.2,
            },
            {
                "game_id": "g3",
                "game_date": "2024-04-01",
                "season": 2024,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_score": 6,
                "away_score": 5,
                "home_team_win": 1,
                "feature_a": 0.7,
            },
            {
                "game_id": "g4",
                "game_date": "2024-04-02",
                "season": 2024,
                "home_team": "AWY",
                "away_team": "HOM",
                "home_score": 1,
                "away_score": 3,
                "home_team_win": 0,
                "feature_a": -0.5,
            },
        ]
    )

    result = run_expected_runs_experiments(features, model_names=["ridge"], holdout_season=2024)

    assert result.metrics.loc[0, "model_name"] == "ridge"
    assert result.metrics.loc[0, "n_games"] == 2
    assert "total_within_2" in result.metrics.columns
    assert set(result.synthetic_ou_metrics["total_line"]) == {6.5, 7.5, 8.5, 9.5, 10.5}
    assert {"ou_accuracy", "pass_rate_0_5", "strong_rate_1_5"}.issubset(result.synthetic_ou_metrics.columns)
    assert result.feature_columns == ["feature_a"]


def test_expected_runs_prediction_features_are_holdout_safe():
    features = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2021-04-01",
                "season": 2021,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_score": 5,
                "away_score": 3,
                "home_team_win": 1,
                "prediction_mode": "confirmed_lineup",
                "feature_a": 0.4,
            },
            {
                "game_id": "g2",
                "game_date": "2021-04-02",
                "season": 2021,
                "home_team": "AWY",
                "away_team": "HOM",
                "home_score": 2,
                "away_score": 4,
                "home_team_win": 0,
                "prediction_mode": "confirmed_lineup",
                "feature_a": -0.2,
            },
            {
                "game_id": "g3",
                "game_date": "2022-04-01",
                "season": 2022,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_score": 6,
                "away_score": 5,
                "home_team_win": 1,
                "prediction_mode": "confirmed_lineup",
                "feature_a": 0.7,
            },
        ]
    )

    augmented = add_expected_runs_prediction_features(
        features,
        holdout_seasons=[2022],
        model_name="ridge",
        prediction_mode="confirmed_lineup",
    )

    assert augmented.loc[augmented["season"] == 2021, "expected_home_runs"].isna().all()
    holdout = augmented.loc[augmented["season"] == 2022].iloc[0]
    assert pd.notna(holdout["expected_home_runs"])
    assert holdout["expected_total_runs"] == holdout["expected_home_runs"] + holdout["expected_away_runs"]
