import pandas as pd

from mlb_winprob.data_sources import write_csv_table
from mlb_winprob.park_factors import build_empirical_park_factors


def test_build_empirical_park_factors_applies_previous_season(tmp_path):
    season_dir = tmp_path / "mlb_stats_api_2024"
    games = pd.DataFrame(
        [
            {
                "game_id": "1",
                "season": 2024,
                "venue_id": 10,
                "venue_name": "Hitter Park",
                "home_score": 8,
                "away_score": 6,
            },
            {
                "game_id": "2",
                "season": 2024,
                "venue_id": 10,
                "venue_name": "Hitter Park",
                "home_score": 7,
                "away_score": 5,
            },
            {
                "game_id": "3",
                "season": 2024,
                "venue_id": 20,
                "venue_name": "Pitcher Park",
                "home_score": 2,
                "away_score": 1,
            },
            {
                "game_id": "4",
                "season": 2024,
                "venue_id": 20,
                "venue_name": "Pitcher Park",
                "home_score": 3,
                "away_score": 1,
            },
        ]
    )
    batting = pd.DataFrame(
        [
            {"game_id": "1", "home_runs": 4},
            {"game_id": "2", "home_runs": 2},
            {"game_id": "3", "home_runs": 0},
            {"game_id": "4", "home_runs": 1},
        ]
    )
    write_csv_table(games, season_dir / "games.csv")
    write_csv_table(batting, season_dir / "batting_logs.csv")

    factors = build_empirical_park_factors([season_dir], min_games=1)

    assert set(factors["season"]) == {2025}
    hitter = factors[factors["venue_id"] == 10].iloc[0]
    pitcher = factors[factors["venue_id"] == 20].iloc[0]
    assert hitter["park_factor_run"] > 1
    assert pitcher["park_factor_run"] < 1
    assert hitter["park_factor_hr"] > 1
