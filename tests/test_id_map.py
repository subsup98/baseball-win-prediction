import pandas as pd

from mlb_winprob.id_map import build_id_map


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
