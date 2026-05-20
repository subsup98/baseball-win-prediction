import pandas as pd

from mlb_winprob.features import FeatureBuilder
from mlb_winprob.schemas import FeatureBuildConfig


def _raw_tables():
    games = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2024-04-01",
                "season": 2024,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_sp_id": "HSP",
                "away_sp_id": "ASP",
                "home_score": 5,
                "away_score": 3,
                "venue_id": "park",
            },
            {
                "game_id": "g2",
                "game_date": "2024-04-05",
                "season": 2024,
                "home_team": "HOM",
                "away_team": "AWY",
                "home_sp_id": "HSP",
                "away_sp_id": "ASP",
                "home_score": 2,
                "away_score": 4,
                "venue_id": "park",
            },
        ]
    )
    batting_rows = []
    for game_id, game_date, home_runs in [("g1", "2024-04-01", 1), ("g2", "2024-04-05", 0)]:
        for index, player_id in enumerate(["H1", "H2", "H3"], start=1):
            batting_rows.append(
                {
                    "game_id": game_id,
                    "game_date": game_date,
                    "season": 2024,
                    "player_id": player_id,
                    "team": "HOM",
                    "opposing_pitcher_hand": "R",
                    "at_bats": 4,
                    "hits": 2 if game_id == "g1" else 0,
                    "doubles": 0,
                    "triples": 0,
                    "home_runs": home_runs if index == 1 else 0,
                    "walks": 1,
                    "hit_by_pitch": 0,
                    "sacrifice_flies": 0,
                    "total_bases": 5 if index == 1 and game_id == "g1" else 2 if game_id == "g1" else 0,
                    "plate_appearances": 5,
                    "statcast_pa": 5,
                    "statcast_batted_balls": 4,
                    "statcast_hard_hit_balls": 2,
                    "statcast_barrels": 1 if game_id == "g1" and index == 1 else 0,
                    "statcast_xwoba_sum": 2.5 if game_id == "g1" else 1.5,
                    "statcast_xwoba_count": 5,
                    "statcast_woba_sum": 2.0 if game_id == "g1" else 1.0,
                    "statcast_woba_count": 5,
                    "statcast_launch_speed_sum": 360,
                }
            )
        for index, player_id in enumerate(["A1", "A2", "A3"], start=1):
            batting_rows.append(
                {
                    "game_id": game_id,
                    "game_date": game_date,
                    "season": 2024,
                    "player_id": player_id,
                    "team": "AWY",
                    "opposing_pitcher_hand": "L",
                    "at_bats": 4,
                    "hits": 1,
                    "doubles": 0,
                    "triples": 0,
                    "home_runs": 0,
                    "walks": 0,
                    "hit_by_pitch": 0,
                    "sacrifice_flies": 0,
                    "total_bases": 1,
                    "plate_appearances": 4,
                    "statcast_pa": 4,
                    "statcast_batted_balls": 4,
                    "statcast_hard_hit_balls": 1,
                    "statcast_barrels": 0,
                    "statcast_xwoba_sum": 1.2,
                    "statcast_xwoba_count": 4,
                    "statcast_woba_sum": 1.0,
                    "statcast_woba_count": 4,
                    "statcast_launch_speed_sum": 330,
                }
            )
    batting_logs = pd.DataFrame(batting_rows)

    pitcher_logs = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2024-04-01",
                "season": 2024,
                "player_id": "HSP",
                "team": "HOM",
                "is_start": 1,
                "innings_pitched": 6,
                "hits": 4,
                "home_runs": 1,
                "walks": 1,
                "hit_by_pitch": 0,
                "strikeouts": 7,
                "batters_faced": 24,
                "pitches": 92,
                "statcast_batters_faced": 24,
                "statcast_batted_balls_allowed": 16,
                "statcast_hard_hit_balls_allowed": 5,
                "statcast_barrels_allowed": 1,
                "statcast_xwoba_allowed_sum": 7.2,
                "statcast_xwoba_allowed_count": 24,
                "statcast_woba_allowed_sum": 7.0,
                "statcast_woba_allowed_count": 24,
                "statcast_launch_speed_allowed_sum": 1400,
            },
            {
                "game_id": "g1",
                "game_date": "2024-04-01",
                "season": 2024,
                "player_id": "ASP",
                "team": "AWY",
                "is_start": 1,
                "innings_pitched": 5,
                "hits": 6,
                "home_runs": 2,
                "walks": 3,
                "hit_by_pitch": 0,
                "strikeouts": 4,
                "batters_faced": 23,
                "pitches": 101,
                "statcast_batters_faced": 23,
                "statcast_batted_balls_allowed": 17,
                "statcast_hard_hit_balls_allowed": 7,
                "statcast_barrels_allowed": 2,
                "statcast_xwoba_allowed_sum": 9.2,
                "statcast_xwoba_allowed_count": 23,
                "statcast_woba_allowed_sum": 9.0,
                "statcast_woba_allowed_count": 23,
                "statcast_launch_speed_allowed_sum": 1500,
            },
            {
                "game_id": "g1",
                "game_date": "2024-04-01",
                "season": 2024,
                "player_id": "HRP",
                "team": "HOM",
                "is_start": 0,
                "innings_pitched": 2,
                "hits": 1,
                "home_runs": 0,
                "walks": 0,
                "hit_by_pitch": 0,
                "strikeouts": 2,
                "batters_faced": 7,
                "pitches": 22,
                "is_closer": 1,
                "is_high_leverage": 1,
            },
            {
                "game_id": "g1",
                "game_date": "2024-04-01",
                "season": 2024,
                "player_id": "ARP",
                "team": "AWY",
                "is_start": 0,
                "innings_pitched": 3,
                "hits": 2,
                "home_runs": 0,
                "walks": 1,
                "hit_by_pitch": 0,
                "strikeouts": 3,
                "batters_faced": 12,
                "pitches": 45,
                "is_closer": 0,
                "is_high_leverage": 1,
            },
            {
                "game_id": "g2",
                "game_date": "2024-04-05",
                "season": 2024,
                "player_id": "HSP",
                "team": "HOM",
                "is_start": 1,
                "innings_pitched": 5,
                "hits": 8,
                "home_runs": 3,
                "walks": 2,
                "hit_by_pitch": 0,
                "strikeouts": 2,
                "batters_faced": 25,
                "pitches": 88,
            },
            {
                "game_id": "g2",
                "game_date": "2024-04-05",
                "season": 2024,
                "player_id": "ASP",
                "team": "AWY",
                "is_start": 1,
                "innings_pitched": 7,
                "hits": 3,
                "home_runs": 0,
                "walks": 1,
                "hit_by_pitch": 0,
                "strikeouts": 8,
                "batters_faced": 26,
                "pitches": 95,
            },
        ]
    )

    lineup_rows = []
    for game_id in ["g1", "g2"]:
        for order, player_id in enumerate(["H1", "H2", "H3"], start=1):
            lineup_rows.append(
                {
                    "game_id": game_id,
                    "team": "HOM",
                    "player_id": player_id,
                    "batting_order": order,
                    "bats": "L" if order == 1 else "R",
                    "prediction_mode": "confirmed_lineup",
                }
            )
        for order, player_id in enumerate(["A1", "A2", "A3"], start=1):
            lineup_rows.append(
                {
                    "game_id": game_id,
                    "team": "AWY",
                    "player_id": player_id,
                    "batting_order": order,
                    "bats": "R",
                    "prediction_mode": "confirmed_lineup",
                }
            )
    lineups = pd.DataFrame(lineup_rows)

    weather = pd.DataFrame(
        [
            {"game_id": "g1", "temperature": 70, "wind_speed": 5, "wind_direction": "out", "humidity": 50, "is_dome": 0},
            {"game_id": "g2", "temperature": 72, "wind_speed": 8, "wind_direction": "in", "humidity": 55, "is_dome": 0},
        ]
    )
    park_factors = pd.DataFrame(
        [
            {"venue_id": "park", "season": 2024, "park_factor_run": 1.02, "park_factor_hr": 1.10},
        ]
    )
    return games, batting_logs, pitcher_logs, lineups, weather, park_factors


def _build_features(batting_logs=None):
    games, default_batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
    return builder.build(
        games=games,
        batting_logs=batting_logs if batting_logs is not None else default_batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
    )


def test_current_game_batting_does_not_leak_into_current_features():
    games, batting_logs, *_ = _raw_tables()
    baseline = _build_features(batting_logs)
    modified = batting_logs.copy()
    mask = (modified["game_id"] == "g2") & (modified["team"] == "HOM")
    modified.loc[mask, ["hits", "home_runs", "total_bases"]] = 100
    changed = _build_features(modified)

    baseline_g2 = baseline.loc[baseline["game_id"] == "g2"].iloc[0]
    changed_g2 = changed.loc[changed["game_id"] == "g2"].iloc[0]
    assert baseline_g2["home_lineup_avg_woba"] == changed_g2["home_lineup_avg_woba"]
    assert baseline_g2["home_team_ops_season_to_date"] == changed_g2["home_team_ops_season_to_date"]


def test_starter_rest_and_diff_direction_are_home_advantage_positive():
    features = _build_features()
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["home_sp_rest_days"] == 4
    assert g2["sp_fip_diff"] == g2["away_sp_fip_season_to_date"] - g2["home_sp_fip_season_to_date"]


def test_bullpen_rolling_usage_and_diff_direction():
    features = _build_features()
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["home_bullpen_ip_last_5d"] == 2
    assert g2["away_bullpen_ip_last_5d"] == 3
    assert g2["bullpen_fatigue_diff"] == g2["away_bullpen_fatigue_score"] - g2["home_bullpen_fatigue_score"]


def test_optional_statcast_quality_features_are_leakage_safe():
    features = _build_features()
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["home_lineup_statcast_xwoba"] > 0
    assert g2["home_lineup_hard_hit_rate"] > 0
    assert g2["home_sp_statcast_xwoba_allowed_to_date"] == 7.2 / 24
    assert g2["sp_statcast_xwoba_allowed_diff"] == (
        g2["away_sp_statcast_xwoba_allowed_to_date"] - g2["home_sp_statcast_xwoba_allowed_to_date"]
    )
