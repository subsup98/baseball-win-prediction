import math
import json

import pandas as pd

from mlb_winprob.standardize import (
    _parse_weather,
    baseball_innings_to_float,
    manual_lineup_template,
    market_lines_template,
    standardize_manual_lineups,
    standardize_mlb_stats_api_boxscores,
)


def test_baseball_innings_to_float_uses_thirds():
    assert baseball_innings_to_float("6.0") == 6.0
    assert baseball_innings_to_float("5.1") == 5 + 1 / 3
    assert baseball_innings_to_float("0.2") == 2 / 3


def test_parse_weather_marks_closed_roof_and_condition():
    parsed = _parse_weather({"Weather": "68 degrees, Roof Closed.", "Wind": "0 mph, None."})

    assert parsed["temperature"] == 68
    assert parsed["wind_speed"] == 0
    assert math.isnan(parsed["wind_direction"])
    assert parsed["is_dome"] == 1
    assert parsed["weather_condition"] == "Roof Closed"
    assert parsed["weather_source"] == "mlb_stats_api_boxscore"


def test_parse_weather_extracts_humidity_when_source_provides_it():
    parsed = _parse_weather({"Weather": "82 degrees, Clear, humidity 57%.", "Wind": "8 mph, Out To RF."})

    assert parsed["humidity"] == 57.0


def test_standardize_mlb_boxscores_preserves_pre_lineup_snapshot_metadata(tmp_path):
    schedule = pd.DataFrame(
        [
            {
                "game_id": "123",
                "game_date": "2026-05-26T23:05:00Z",
                "season": 2026,
                "home_team_abbrev": "HOM",
                "away_team_abbrev": "AWY",
                "home_sp_id": 100,
                "away_sp_id": 200,
                "venue_id": 1,
                "venue_name": "Example Park",
            }
        ]
    )
    schedule_path = tmp_path / "schedule.csv"
    schedule.to_csv(schedule_path, index=False)
    boxscore_dir = tmp_path / "boxscores"
    boxscore_dir.mkdir()
    boxscore = {
        "teams": {
            "home": {
                "battingOrder": [1],
                "players": {"ID1": {"person": {"id": 1, "fullName": "Home Hitter"}, "stats": {}}},
            },
            "away": {
                "battingOrder": [2],
                "players": {"ID2": {"person": {"id": 2, "fullName": "Away Hitter"}, "stats": {}}},
            },
        },
        "info": [],
    }
    (boxscore_dir / "123_boxscore.json").write_text(json.dumps(boxscore), encoding="utf-8")

    outputs = standardize_mlb_stats_api_boxscores(
        schedule_csv=schedule_path,
        boxscore_dir=boxscore_dir,
        output_dir=tmp_path / "standardized",
        prediction_mode="pre_lineup",
        lineup_source="mlb_stats_api_boxscore_snapshot",
        captured_at="2026-05-26T20:00:00Z",
        lineup_confidence=1.0,
    )

    lineups = pd.read_csv(outputs["lineups"])

    assert lineups.shape[0] == 2
    assert set(lineups["prediction_mode"]) == {"pre_lineup"}
    assert set(lineups["lineup_source"]) == {"mlb_stats_api_boxscore_snapshot"}
    assert set(lineups["captured_at"]) == {"2026-05-26T20:00:00Z"}
    assert set(lineups["lineup_confidence"]) == {1.0}
    assert set(lineups["is_expected_starter"]) == {1.0}


def test_standardize_mlb_boxscores_writes_headers_for_empty_pregame_tables(tmp_path):
    schedule = pd.DataFrame(
        [
            {
                "game_id": "123",
                "game_date": "2026-05-26T23:05:00Z",
                "season": 2026,
                "home_team_abbrev": "HOM",
                "away_team_abbrev": "AWY",
                "venue_id": 1,
                "venue_name": "Example Park",
            }
        ]
    )
    schedule_path = tmp_path / "schedule.csv"
    schedule.to_csv(schedule_path, index=False)
    boxscore_dir = tmp_path / "boxscores"
    boxscore_dir.mkdir()
    boxscore = {
        "teams": {
            "home": {"players": {}},
            "away": {"players": {}},
        },
        "info": [],
    }
    (boxscore_dir / "123_boxscore.json").write_text(json.dumps(boxscore), encoding="utf-8")

    outputs = standardize_mlb_stats_api_boxscores(
        schedule_csv=schedule_path,
        boxscore_dir=boxscore_dir,
        output_dir=tmp_path / "standardized",
        prediction_mode="pre_lineup",
        lineup_source="mlb_stats_api_boxscore_snapshot",
        captured_at="2026-05-26T20:00:00Z",
    )

    lineups = pd.read_csv(outputs["lineups"])
    batting_logs = pd.read_csv(outputs["batting_logs"])
    pitcher_logs = pd.read_csv(outputs["pitcher_logs"])

    assert lineups.empty
    assert {"game_id", "team", "player_id", "prediction_mode", "captured_at"}.issubset(lineups.columns)
    assert batting_logs.empty
    assert {"game_id", "player_id", "plate_appearances"}.issubset(batting_logs.columns)
    assert pitcher_logs.empty
    assert {"game_id", "player_id", "innings_pitched"}.issubset(pitcher_logs.columns)


def test_manual_lineup_template_creates_nine_slots_per_team():
    games = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2026-05-26",
                "home_team": "HOM",
                "away_team": "AWY",
            }
        ]
    )

    template = manual_lineup_template(games)

    assert template.shape[0] == 18
    assert set(template["team"]) == {"HOM", "AWY"}
    assert template.groupby("team")["batting_order"].max().to_dict() == {"AWY": 9, "HOM": 9}


def test_market_lines_template_creates_one_editable_row_per_game():
    games = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "game_date": "2026-05-26",
                "home_team": "HOM",
                "away_team": "AWY",
                "home_sp_id": 100,
                "away_sp_id": 200,
            }
        ]
    )

    template = market_lines_template(games)

    assert template.shape[0] == 1
    assert template.loc[0, "game_id"] == "g1"
    assert template.loc[0, "home_sp_id_at_open"] == 100
    assert {"opening_total_line", "current_total_line", "over_odds", "under_odds"}.issubset(template.columns)


def test_standardize_manual_lineups_maps_names_and_preserves_metadata():
    manual = pd.DataFrame(
        [
            {
                "game_id": "g1",
                "team": "HOM",
                "batting_order": 1,
                "player_name": "Test Player Jr.",
                "bats": "L",
                "lineup_confidence": 0.7,
            },
            {
                "game_id": "g1",
                "team": "HOM",
                "batting_order": 2,
                "player_id": 999,
                "player_name": "Known Id",
                "bats": "R",
            },
        ]
    )
    id_map = pd.DataFrame(
        [
            {
                "mlbam_id": "123",
                "name_first": "Test",
                "name_last": "Player",
                "name_given": "Test Player",
                "mlb_played_first": 2020,
                "mlb_played_last": 2026,
            }
        ]
    )

    lineups = standardize_manual_lineups(
        manual,
        id_map=id_map,
        season=2026,
        prediction_mode="projected",
        captured_at="2026-05-26T20:00:00Z",
    )

    assert lineups["player_id"].tolist() == [123.0, 999.0]
    assert lineups["prediction_mode"].tolist() == ["projected", "projected"]
    assert lineups["lineup_source"].tolist() == ["manual", "manual"]
    assert lineups["captured_at"].tolist() == ["2026-05-26T20:00:00Z", "2026-05-26T20:00:00Z"]
    assert lineups["lineup_confidence"].tolist() == [0.7, 0.6]
