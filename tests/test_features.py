import pandas as pd
import pytest

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
                "venue_latitude": 40.0,
                "venue_longitude": -75.0,
                "venue_timezone_offset": -4,
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
                "venue_latitude": 34.0,
                "venue_longitude": -118.0,
                "venue_timezone_offset": -7,
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
                "statcast_pitches": 92,
                "statcast_whiffs": 12,
                "statcast_batted_balls_allowed": 16,
                "statcast_hard_hit_balls_allowed": 5,
                "statcast_barrels_allowed": 1,
                "statcast_xwoba_allowed_sum": 7.2,
                "statcast_xwoba_allowed_count": 24,
                "statcast_woba_allowed_sum": 7.0,
                "statcast_woba_allowed_count": 24,
                "statcast_launch_speed_allowed_sum": 1400,
                "statcast_release_speed_sum": 92 * 95,
                "statcast_release_speed_count": 92,
                "statcast_fastball_release_speed_sum": 65 * 96,
                "statcast_fastball_release_speed_count": 65,
                "statcast_spin_rate_sum": 92 * 2300,
                "statcast_spin_rate_count": 92,
                "statcast_pitch_ff": 50,
                "statcast_pitch_si": 10,
                "statcast_pitch_fc": 5,
                "statcast_pitch_sl": 20,
                "statcast_pitch_cu": 5,
                "statcast_pitch_ch": 2,
                "statcast_pitch_fs": 0,
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
                "statcast_pitches": 101,
                "statcast_whiffs": 8,
                "statcast_batted_balls_allowed": 17,
                "statcast_hard_hit_balls_allowed": 7,
                "statcast_barrels_allowed": 2,
                "statcast_xwoba_allowed_sum": 9.2,
                "statcast_xwoba_allowed_count": 23,
                "statcast_woba_allowed_sum": 9.0,
                "statcast_woba_allowed_count": 23,
                "statcast_launch_speed_allowed_sum": 1500,
                "statcast_release_speed_sum": 101 * 93,
                "statcast_release_speed_count": 101,
                "statcast_fastball_release_speed_sum": 55 * 94,
                "statcast_fastball_release_speed_count": 55,
                "statcast_spin_rate_sum": 101 * 2200,
                "statcast_spin_rate_count": 101,
                "statcast_pitch_ff": 45,
                "statcast_pitch_si": 5,
                "statcast_pitch_fc": 5,
                "statcast_pitch_sl": 25,
                "statcast_pitch_cu": 10,
                "statcast_pitch_ch": 10,
                "statcast_pitch_fs": 1,
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
                "saves": 1,
                "holds": 0,
                "games_finished": 1,
                "save_opportunities": 1,
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
                "saves": 0,
                "holds": 1,
                "games_finished": 0,
                "save_opportunities": 0,
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
                    "lineup_confidence": 0.95,
                    "is_available": 1,
                    "is_expected_starter": 1,
                    "rest_signal": 0,
                    "injury_status": "",
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
                    "lineup_confidence": 0.90,
                    "is_available": 1,
                    "is_expected_starter": 1,
                    "rest_signal": 1 if game_id == "g2" and order == 3 else 0,
                    "injury_status": "out" if game_id == "g2" and order == 3 else "",
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
    assert g2["home_sp_whiff_rate_to_date"] == 12 / 92
    assert g2["home_sp_avg_fastball_velocity_to_date"] == 96
    assert g2["home_sp_fastball_usage_to_date"] == (50 + 10 + 5) / 92


def test_public_data_proxy_features_are_available_without_statcast_columns():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    batting_logs = batting_logs.drop(columns=[column for column in batting_logs.columns if column.startswith("statcast_")])
    pitcher_logs = pitcher_logs.drop(columns=[column for column in pitcher_logs.columns if column.startswith("statcast_")])
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))

    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
    )
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert pd.isna(g2["home_lineup_statcast_xwoba"])
    assert g2["home_lineup_xwoba_proxy"] > 0
    assert g2["home_lineup_hard_contact_proxy"] > 0
    assert pd.isna(g2["home_sp_whiff_rate_to_date"])
    assert g2["home_sp_whiff_proxy"] == 7 / 24
    assert g2["sp_run_prevention_proxy_diff"] == g2["away_sp_run_prevention_proxy"] - g2["home_sp_run_prevention_proxy"]


def test_lineup_platoon_features_use_opposing_starter_hand():
    features = _build_features()
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["home_lineup_platoon_woba"] == g2["home_lineup_vs_rhp_woba"]
    assert g2["away_lineup_platoon_woba"] == g2["away_lineup_vs_lhp_woba"]
    assert g2["home_lineup_platoon_advantage_ratio"] == 1 / 3
    assert g2["away_lineup_platoon_advantage_ratio"] == 1.0
    assert g2["lineup_platoon_woba_diff"] == g2["home_lineup_platoon_woba"] - g2["away_lineup_platoon_woba"]
    assert g2["lineup_platoon_advantage_diff"] == (
        g2["home_lineup_platoon_advantage_ratio"] - g2["away_lineup_platoon_advantage_ratio"]
    )


def test_lineup_confidence_absence_travel_and_bullpen_role_features():
    features = _build_features()
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["home_lineup_confidence"] == pytest.approx(0.95)
    assert g2["away_lineup_confidence"] == pytest.approx(0.90)
    assert g2["away_lineup_injury_absence_signal_count"] == 1
    assert g2["away_lineup_rest_signal_count"] == 1
    assert g2["home_lineup_previous_starter_return_rate"] == 1.0
    assert g2["home_travel_rest_days"] == 4
    assert g2["home_travel_distance_miles"] > 2000
    assert g2["home_travel_timezone_shift"] == -3
    assert g2["home_estimated_high_leverage_role_fatigue_score"] == 0


def test_pre_lineup_mode_does_not_fall_back_to_confirmed_rows():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="pre_lineup"))

    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
    )
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert features["prediction_mode"].eq("pre_lineup").all()
    assert pd.isna(g2["home_lineup_player_count"])
    assert pd.isna(g2["away_lineup_confidence"])


def test_pre_lineup_mode_uses_projected_alias_rows():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    projected = lineups.copy()
    projected["prediction_mode"] = "projected"
    projected["lineup_confidence"] = 0.55
    combined_lineups = pd.concat([lineups, projected], ignore_index=True)
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="pre_lineup"))

    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=combined_lineups,
        weather=weather,
        park_factors=park_factors,
    )
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert features["prediction_mode"].eq("pre_lineup").all()
    assert g2["home_lineup_player_count"] == 3
    assert g2["home_lineup_confidence"] == pytest.approx(0.55)


def test_pre_lineup_projected_rows_can_include_game_date_without_season():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    projected = lineups.copy()
    projected["prediction_mode"] = "projected"
    projected = projected.merge(games[["game_id", "game_date"]], on="game_id", how="left")
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="pre_lineup"))

    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=projected,
        weather=weather,
        park_factors=park_factors,
    )

    assert features["prediction_mode"].eq("pre_lineup").all()
    assert features.loc[features["game_id"] == "g2", "home_lineup_player_count"].iloc[0] == 3


def test_estimated_high_leverage_role_score_is_capped_for_fatigue():
    games, _, pitcher_logs, *_ = _raw_tables()
    games = pd.concat(
        [
            games,
            pd.DataFrame(
                [
                    {
                        "game_id": "g3",
                        "game_date": "2024-04-06",
                        "season": 2024,
                        "home_team": "HOM",
                        "away_team": "AWY",
                        "home_sp_id": "HSP",
                        "away_sp_id": "ASP",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    pitcher_logs = pd.concat(
        [
            pitcher_logs,
            pd.DataFrame(
                [
                    {
                        "game_id": "g2",
                        "game_date": "2024-04-05",
                        "season": 2024,
                        "player_id": "HRP",
                        "team": "HOM",
                        "is_start": 0,
                        "innings_pitched": 1,
                        "hits": 0,
                        "home_runs": 0,
                        "walks": 0,
                        "hit_by_pitch": 0,
                        "strikeouts": 1,
                        "is_closer": 0,
                        "is_high_leverage": 0,
                        "saves": 0,
                        "holds": 0,
                        "games_finished": 0,
                        "save_opportunities": 0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    games["game_date"] = pd.to_datetime(games["game_date"])
    pitcher_logs["game_date"] = pd.to_datetime(pitcher_logs["game_date"])
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))

    bullpen = builder._compute_bullpen_features(games, pitcher_logs)
    g3_home = bullpen[(bullpen["game_id"] == "g3") & (bullpen["team"] == "HOM")].iloc[0]

    assert g3_home["estimated_high_leverage_role_fatigue_score"] == pytest.approx(1.0)


def test_market_line_features_include_lines_odds_movement_and_starter_changes():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    market_lines = pd.DataFrame(
        [
            {
                "game_id": "g2",
                "opening_total_line": 8.5,
                "current_total_line": 9.0,
                "closing_total_line": 9.5,
                "over_odds": -110,
                "under_odds": -105,
                "opening_home_moneyline": -120,
                "current_home_moneyline": -135,
                "opening_away_moneyline": 110,
                "current_away_moneyline": 125,
                "home_sp_id_at_open": "OLD_HSP",
                "away_sp_id_at_open": "ASP",
            }
        ]
    )
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))

    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
        market_lines=market_lines,
    )
    g2 = features.loc[features["game_id"] == "g2"].iloc[0]

    assert g2["market_total_line"] == 9.0
    assert g2["market_closing_total_line"] == 9.5
    assert g2["market_total_line_movement"] == 0.5
    assert g2["market_over_implied_prob"] == pytest.approx(110 / 210)
    assert g2["market_home_moneyline_movement"] == -15
    assert g2["market_away_moneyline_movement"] == 15
    assert g2["market_home_sp_changed"] == 1.0
    assert g2["market_away_sp_changed"] == 0.0
    assert g2["market_starter_change_count"] == 1.0


def test_recent_form_features_use_only_prior_games():
    games, batting_logs, pitcher_logs, lineups, weather, park_factors = _raw_tables()
    games = pd.concat(
        [
            games,
            pd.DataFrame(
                [
                    {
                        "game_id": "g3",
                        "game_date": "2024-04-09",
                        "season": 2024,
                        "home_team": "HOM",
                        "away_team": "AWY",
                        "home_sp_id": "HSP",
                        "away_sp_id": "ASP",
                        "home_score": 1,
                        "away_score": 0,
                        "venue_id": "park",
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))

    team_features = builder._compute_team_features(games, batting_logs)
    g1_home = team_features[(team_features["game_id"] == "g1") & (team_features["team"] == "HOM")].iloc[0]
    g2_home = team_features[(team_features["game_id"] == "g2") & (team_features["team"] == "HOM")].iloc[0]
    g3_home = team_features[(team_features["game_id"] == "g3") & (team_features["team"] == "HOM")].iloc[0]

    assert pd.isna(g1_home["team_weighted_win_rate_last_10"])
    assert g2_home["team_weighted_win_rate_last_10"] == pytest.approx(1.0)
    assert g2_home["team_low_run_rate_last_10"] == pytest.approx(0.0)
    assert g3_home["team_weighted_win_rate_last_10"] == pytest.approx(0.45945945945945943)
    assert g3_home["team_low_run_rate_last_10"] == pytest.approx(0.5)
    assert g3_home["team_5plus_run_rate_last_10"] == pytest.approx(0.5)
    assert g3_home["team_runs_for_volatility_last_10"] == pytest.approx(2.1213203435596424)
    assert g3_home["team_pythagorean_win_pct_last_20"] == pytest.approx(0.5)
    assert g3_home["team_actual_minus_pythag_last_20"] == pytest.approx(0.0)
