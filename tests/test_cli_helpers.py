import pandas as pd

from mlb_winprob.cli import _readable_prediction_table, kst_date_to_mlb_date


def test_kst_date_to_mlb_date_uses_previous_us_slate():
    assert kst_date_to_mlb_date("2026-05-28") == "2026-05-27"


def test_readable_prediction_table_adds_recommendation_and_winning_score():
    predictions = pd.DataFrame(
        {
            "game_id": ["1"],
            "game_date": ["2026-05-27 17:07:00+00:00"],
            "home_team": ["TOR"],
            "away_team": ["MIA"],
            "home_win_probability": [0.526],
            "away_win_probability": [0.474],
            "win_pick": ["TOR"],
            "pred_home_score": [4.2],
            "pred_away_score": [4.8],
        }
    )
    schedule = pd.DataFrame({"game_id": ["1"], "status": ["Scheduled"]})

    readable = _readable_prediction_table(predictions, schedule=schedule, korean=False)

    assert readable.loc[0, "matchup"] == "MIA @ TOR"
    assert readable.loc[0, "recommendation"] == "pass"
    assert readable.loc[0, "score_prediction"] == "TOR 6:5 승"
