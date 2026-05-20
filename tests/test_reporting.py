import pandas as pd

from mlb_winprob.reporting import feature_quality_tables, write_feature_quality_report


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
