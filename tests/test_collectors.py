import pandas as pd

from mlb_winprob.data_sources import MLBStatsApiCollector, default_collection_workers


def test_normalize_mlb_schedule_keeps_backbone_columns():
    payload = {
        "dates": [
            {
                "date": "2024-04-01",
                "games": [
                    {
                        "gamePk": 123,
                        "gameDate": "2024-04-01T23:05:00Z",
                        "season": "2024",
                        "gameType": "R",
                        "status": {"detailedState": "Final"},
                        "venue": {"id": 1, "name": "Example Park"},
                        "teams": {
                            "home": {
                                "score": 5,
                                "team": {"id": 10, "name": "Home Club", "abbreviation": "HOM"},
                                "probablePitcher": {"id": 100, "fullName": "Home Starter"},
                            },
                            "away": {
                                "score": 3,
                                "team": {"id": 20, "name": "Away Club", "abbreviation": "AWY"},
                                "probablePitcher": {"id": 200, "fullName": "Away Starter"},
                            },
                        },
                    }
                ],
            }
        ]
    }

    frame = MLBStatsApiCollector.normalize_schedule(payload)

    assert len(frame) == 1
    row = frame.iloc[0]
    assert row["game_id"] == 123
    assert row["home_team"] == "Home Club"
    assert row["away_team"] == "Away Club"
    assert row["home_sp_id"] == 100
    assert row["away_sp_id"] == 200
    assert row["venue_id"] == 1
    assert pd.notna(row["game_date"])


def test_people_metadata_normalization(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    def fake_fetch_json(url, params=None):
        assert params == {"personIds": "100,200"}
        return {
            "people": [
                {
                    "id": 100,
                    "fullName": "Left Batter",
                    "batSide": {"code": "L"},
                    "pitchHand": {"code": "R"},
                    "primaryPosition": {"abbreviation": "OF"},
                },
                {
                    "id": 200,
                    "fullName": "Right Pitcher",
                    "batSide": {"code": "R"},
                    "pitchHand": {"code": "R"},
                    "primaryPosition": {"abbreviation": "P"},
                },
            ]
        }

    monkeypatch.setattr(data_sources, "fetch_json", fake_fetch_json)
    frame = MLBStatsApiCollector().people([200, 100, 100])

    assert frame.shape == (2, 5)
    assert frame.loc[frame["player_id"] == 100, "bats"].iloc[0] == "L"
    assert frame.loc[frame["player_id"] == 200, "throws"].iloc[0] == "R"


def test_game_feed_uses_v11_endpoint(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    captured = {}

    def fake_fetch_json(url, params=None):
        captured["url"] = url
        captured["params"] = params
        return {"gamePk": 123}

    monkeypatch.setattr(data_sources, "fetch_json", fake_fetch_json)

    payload = MLBStatsApiCollector().game_feed(123)

    assert payload == {"gamePk": 123}
    assert captured["url"] == "https://statsapi.mlb.com/api/v1.1/game/123/feed/live"
    assert captured["params"] is None


def test_venues_collects_default_coordinates(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    def fake_fetch_json(url, params=None):
        assert url == "https://statsapi.mlb.com/api/v1/venues/2"
        assert params == {"hydrate": "location"}
        return {
            "venues": [
                {
                    "id": 2,
                    "name": "Oriole Park at Camden Yards",
                    "location": {
                        "city": "Baltimore",
                        "state": "Maryland",
                        "country": "USA",
                        "defaultCoordinates": {"latitude": 39.283787, "longitude": -76.621689},
                    },
                }
            ]
        }

    monkeypatch.setattr(data_sources, "fetch_json", fake_fetch_json)

    frame = MLBStatsApiCollector().venues([2])

    assert frame.loc[0, "venue_id"] == 2
    assert frame.loc[0, "latitude"] == 39.283787
    assert frame.loc[0, "longitude"] == -76.621689


def test_venues_uses_coordinate_fallback(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    def fake_fetch_json(url, params=None):
        return {
            "venues": [
                {
                    "id": 5340,
                    "name": "Estadio Alfredo Harp Helu",
                    "location": {"city": "Mexico City", "country": "Mexico"},
                }
            ]
        }

    monkeypatch.setattr(data_sources, "fetch_json", fake_fetch_json)

    frame = MLBStatsApiCollector().venues([5340])

    assert frame.loc[0, "latitude"] == 19.403611
    assert frame.loc[0, "longitude"] == -99.085278


def test_default_collection_workers_uses_cpu_count(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    monkeypatch.setattr(data_sources.os, "cpu_count", lambda: 6)

    assert default_collection_workers() == 12


def test_default_collection_workers_is_capped(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    monkeypatch.setattr(data_sources.os, "cpu_count", lambda: 64)

    assert default_collection_workers() == 32


def test_save_boxscores_parallel_progress_and_skip(tmp_path):
    collector = MLBStatsApiCollector()
    existing = tmp_path / "1_boxscore.json"
    existing.write_text('{"cached": true}', encoding="utf-8")

    def fake_boxscore(game_id):
        return {"game_id": game_id}

    progress_events = []
    collector.boxscore = fake_boxscore

    paths = collector.save_boxscores(
        ["1", "2", "3"],
        tmp_path,
        workers=2,
        progress_callback=lambda downloaded, skipped, failed, total: progress_events.append(
            (downloaded, skipped, failed, total)
        ),
    )

    assert paths == [
        tmp_path / "1_boxscore.json",
        tmp_path / "2_boxscore.json",
        tmp_path / "3_boxscore.json",
    ]
    assert (tmp_path / "2_boxscore.json").exists()
    assert (tmp_path / "3_boxscore.json").exists()
    assert progress_events[-1] == (2, 1, 0, 3)
