import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from mlb_winprob.reporting import (
    feature_importance_table,
    feature_quality_tables,
    shap_importance_table,
    write_calibration_plot,
    write_feature_importance_summary,
    write_feature_quality_report,
    write_shap_importance_summary,
)


def test_feature_quality_tables_include_null_and_rolling_readiness():
    features = pd.DataFrame(
        [
            {
                "game_id": "1",
                "game_date": "2024-04-01",
                "season": 2024,
                "home_team_win": 1,
                "home_sp_fip_season_to_date": None,
                "home_team_recent_7g_win_rate": None,
            },
            {
                "game_id": "2",
                "game_date": "2024-05-01",
                "season": 2024,
                "home_team_win": 0,
                "home_sp_fip_season_to_date": 4.2,
                "home_team_recent_7g_win_rate": 0.5,
            },
        ]
    )

    tables = feature_quality_tables(features)

    null_rates = tables["null_rates"].set_index("column")
    assert null_rates.loc["home_sp_fip_season_to_date", "null_rate"] == 0.5
    assert tables["season_summary"].loc[0, "rows"] == 2
    readiness = tables["rolling_readiness"]
    assert "home_team_recent_7g_win_rate" in readiness["column"].tolist()


def test_write_feature_quality_report(tmp_path):
    features = pd.DataFrame(
        [
            {
                "game_id": "1",
                "game_date": "2024-05-01",
                "season": 2024,
                "home_team_win": 1,
                "home_sp_rest_days": 5,
            }
        ]
    )

    paths = write_feature_quality_report(features, tmp_path)

    assert paths["null_rates"].exists()
    assert paths["season_summary"].exists()
    assert paths["rolling_readiness"].exists()
    assert paths["summary"].exists()


def test_write_calibration_plot(tmp_path):
    table = pd.DataFrame(
        [
            {"n_games": 10, "predicted_home_win_rate": 0.25, "actual_home_win_rate": 0.2},
            {"n_games": 12, "predicted_home_win_rate": 0.55, "actual_home_win_rate": 0.5},
            {"n_games": 8, "predicted_home_win_rate": 0.75, "actual_home_win_rate": 0.875},
        ]
    )

    path = write_calibration_plot(table, tmp_path / "calibration.png", title="Test")

    assert path is not None
    assert path.exists()
    assert path.stat().st_size > 0


def test_feature_importance_table_extracts_pipeline_model_importances(tmp_path):
    estimator = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(n_estimators=10, random_state=42)),
        ]
    )
    x = pd.DataFrame({"a": [0, 1, 0, 1, 1, 0], "b": [1, 1, 0, 0, 1, 0]})
    y = pd.Series([0, 1, 0, 1, 1, 0])
    estimator.fit(x, y)

    table = feature_importance_table(estimator, ["a", "b"])
    summary = write_feature_importance_summary({(2024, "random_forest"): table}, tmp_path / "summary.md", top_n=2)

    assert table["feature"].tolist()
    assert table["importance"].sum() > 0
    assert summary.exists()
    assert "random_forest" in summary.read_text(encoding="utf-8")


def test_shap_importance_table_returns_empty_without_available_explainer(tmp_path):
    estimator = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", RandomForestClassifier(n_estimators=10, random_state=42)),
        ]
    )
    x = pd.DataFrame({"a": [0, 1, 0, 1, 1, 0], "b": [1, 1, 0, 0, 1, 0]})
    y = pd.Series([0, 1, 0, 1, 1, 0])
    estimator.fit(x, y)

    table = shap_importance_table(estimator, x, ["a", "b"])
    summary = write_shap_importance_summary({} if table.empty else {(2024, "random_forest"): table}, tmp_path / "summary.md")

    assert set(table.columns).issubset({"feature", "mean_abs_shap", "mean_shap", "shap_share"})
    assert summary.exists()
    assert "SHAP" in summary.read_text(encoding="utf-8")
