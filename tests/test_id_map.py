import pandas as pd

from mlb_winprob.id_map import build_external_game_id_map, build_external_player_id_map, build_id_map


def test_build_id_map_normalizes_ids_and_merges_mlb_metadata():
    chadwick = pd.DataFrame(
        [
            {
                "key_person": "abc123",
                "key_uuid": "uuid",
                "key_mlbam": 123.0,
                "key_retro": "testp001",
                "key_bbref": "testpl01",
                "key_bbref_minors": "",
                "key_fangraphs": 456.0,
                "key_wikidata": "Q1",
                "name_first": "Test",
                "name_last": "Player",
                "name_given": "Test Player",
                "name_suffix": "",
                "birth_year": 1990,
                "birth_month": 1,
                "birth_day": 2,
                "mlb_played_first": 2020,
                "mlb_played_last": 2024,
            }
        ]
    )
    mlb_people = pd.DataFrame(
        [
            {
                "player_id": 123,
                "player_name": "Test Player",
                "bats": "R",
                "throws": "L",
                "primary_position": "P",
            }
        ]
    )

    id_map = build_id_map(chadwick, mlb_people)

    assert id_map.loc[0, "mlbam_id"] == "123"
    assert id_map.loc[0, "retrosheet_id"] == "testp001"
    assert id_map.loc[0, "fangraphs_id"] == "456"
    assert id_map.loc[0, "throws"] == "L"


def test_build_external_player_id_map_matches_unique_active_name():
    provider_lineups = pd.DataFrame(
        [
            {"external_player_id": "bdl-1", "player_name": "Test Player Jr."},
            {"external_player_id": "bdl-2", "player_name": "Ambiguous Name"},
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
            },
            {
                "mlbam_id": "456",
                "name_first": "Ambiguous",
                "name_last": "Name",
                "name_given": "Ambiguous Name",
                "mlb_played_first": 2020,
                "mlb_played_last": 2026,
            },
            {
                "mlbam_id": "789",
                "name_first": "Ambiguous",
                "name_last": "Name",
                "name_given": "Ambiguous Name",
                "mlb_played_first": 2020,
                "mlb_played_last": 2026,
            },
        ]
    )

    player_map = build_external_player_id_map(provider_lineups, id_map, season=2026)

    assert player_map.shape == (1, 4)
    assert player_map.loc[0, "external_player_id"] == "bdl-1"
    assert player_map.loc[0, "player_id"] == "123"


def test_build_external_game_id_map_matches_date_and_team_pair():
    provider_lineups = pd.DataFrame(
        [
            {
                "external_game_id": "bdl-game-1",
                "game_date": "2026-05-26T23:05:00Z",
                "home_team": "NYY",
                "away_team": "BOS",
            }
        ]
    )
    mlb_games = pd.DataFrame(
        [
            {
                "game_id": "778001",
                "game_date": "2026-05-26 23:05:00+00:00",
                "home_team": "NYY",
                "away_team": "BOS",
            },
            {
                "game_id": "778002",
                "game_date": "2026-05-26 23:10:00+00:00",
                "home_team": "LAD",
                "away_team": "SF",
            },
        ]
    )

    game_map = build_external_game_id_map(provider_lineups, mlb_games)

    assert game_map.shape == (1, 5)
    assert game_map.loc[0, "external_game_id"] == "bdl-game-1"
    assert game_map.loc[0, "game_id"] == "778001"
