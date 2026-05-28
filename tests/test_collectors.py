import pandas as pd

from mlb_winprob.data_sources import (
    BallDontLieMLBCollector,
    BaseballDataJPCollector,
    MLBStatsApiCollector,
    MyKBOStatsCollector,
    NPBOfficialCollector,
    ProEyeKyuuCollector,
    default_collection_workers,
)
from mlb_winprob.kbo import standardize_mykbo_game_tables, standardize_mykbo_schedule_links, standardize_mykbo_tables
from mlb_winprob.npb import (
    standardize_proeyekyuu_game_results,
    standardize_proeyekyuu_game_tables,
    standardize_proeyekyuu_tables,
    write_npb_feature_set,
    write_npb_model_ready_features,
    write_npb_games_with_venues,
    write_npb_venue_template,
    write_proeyekyuu_batting_detail_audit,
    write_proeyekyuu_coverage_report,
    write_proeyekyuu_games_with_starters,
)


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


def test_mykbo_page_url_uses_known_page_key():
    collector = MyKBOStatsCollector()

    assert collector.page_url("batting_ops", 2025) == "https://mykbostats.com/stats/top/ops/2025"
    assert collector.page_url("schedule", 2025) == "https://mykbostats.com/schedule/2025"
    assert collector.schedule_week_url("2025-04-01") == "https://mykbostats.com/schedule/week_of/2025-04-01"


def test_npb_source_collectors_use_limited_source_urls():
    assert NPBOfficialCollector().page_url("abbreviations") == "https://npb.jp/eng/home/abbreviations.html"
    assert ProEyeKyuuCollector().page_url("player_batting_stats") == "https://proeyekyuu.com/player-batting-stats/"
    assert ProEyeKyuuCollector().page_url("game_results") == "https://proeyekyuu.com/game-results-table/"
    assert BaseballDataJPCollector().page_url("central_pitching_leaders", 2025) == "https://baseballdata.jp/en/2025/cptop.html"


def test_proeyekyuu_game_results_payload_filters_season():
    payload = ProEyeKyuuCollector._game_results_request_payload(nonce="abc123", season=2026, start=10, length=25)

    assert payload["wdtNonce"] == "abc123"
    assert payload["start"] == 10
    assert payload["length"] == 25
    assert payload["columns[2][name]"] == "Season"
    assert payload["columns[2][search][value]"] == "2026"
    assert payload["order[0][column]"] == 3


def test_mykbo_parse_html_tables_and_links(tmp_path):
    html = """
    <html>
      <body>
        <main>
        <a href="/players/1">Player One</a>
        <h3>Tuesday April 1, 2025</h3>
        <table>
          <tr><th>Player</th><th>OPS</th></tr>
          <tr><td>Player One</td><td>.900</td></tr>
        </table>
        </main>
      </body>
    </html>
    """
    html_path = tmp_path / "schedule_week_of_2025-04-01.html"
    html_path.write_text(html, encoding="utf-8")

    tables = MyKBOStatsCollector.parse_html_tables(html)
    paths = MyKBOStatsCollector.write_html_tables(html_path, tmp_path / "parsed")

    assert len(tables) == 1
    assert tables[0].loc[0, "Player"] == "Player One"
    assert (tmp_path / "parsed" / "schedule_week_of_2025-04-01_table_1.csv").exists()
    assert (tmp_path / "parsed" / "schedule_week_of_2025-04-01_links.csv").exists()
    assert (tmp_path / "parsed" / "schedule_week_of_2025-04-01_text.csv").exists()
    assert len(paths) == 3


def test_proeyekyuu_parse_html_tables_and_links(tmp_path):
    html = """
    <html>
      <body>
        <a href="/player/?PlayerID=01005159">Suzuki, Kyo</a>
        <div class="wpDataTablesWrapper" data-wpdatatable_id="9">
          <div class="wpDataTableFilterSection"><label>Season:</label></div>
          <div class="wpDataTableFilterSection"><label>Name:</label></div>
        </div>
        <iframe id="advanced_iframe" title="Game Results" src="https://app.powerbi.com/view?r=test"></iframe>
        <table>
          <tr><th>Season</th><th>Name</th><th>PlayerID</th><th>Team</th><th>PA</th></tr>
          <tr><td>2026</td><td>Suzuki, Kyo</td><td>01005159</td><td>Swallows</td><td>61</td></tr>
        </table>
      </body>
    </html>
    """
    html_path = tmp_path / "player_batting_stats.html"
    html_path.write_text(html, encoding="utf-8")

    paths = ProEyeKyuuCollector.write_html_tables(html_path, tmp_path / "parsed")

    assert (tmp_path / "parsed" / "player_batting_stats_table_1.csv").exists()
    assert (tmp_path / "parsed" / "player_batting_stats_links.csv").exists()
    assert (tmp_path / "parsed" / "player_batting_stats_dynamic_tables.csv").exists()
    assert (tmp_path / "parsed" / "player_batting_stats_iframes.csv").exists()
    assert len(paths) == 4


def test_proeyekyuu_static_table_parser_preserves_duplicate_headers():
    html = """
    <table>
      <thead><tr><th>GameID</th><th>GameID</th><th>Team</th></tr></thead>
      <tbody>
        <tr><td>row-1</td><td>game-1</td><td>Home</td></tr>
      </tbody>
    </table>
    """

    tables = ProEyeKyuuCollector.extract_static_html_tables(html)

    assert tables[0].columns.tolist() == ["GameID", "GameID_2", "Team"]
    assert tables[0].loc[0, "GameID_2"] == "game-1"


def test_proeyekyuu_save_game_pages_fetches_game_ids(tmp_path):
    collector = ProEyeKyuuCollector(base_url="https://example.test")
    fetched = []

    def fake_fetch_text(url, *, headers=None):
        fetched.append((url, headers))
        return "<html><main>Game</main></html>"

    import mlb_winprob.data_sources as data_sources

    original = data_sources.fetch_text
    data_sources.fetch_text = fake_fetch_text
    try:
        games = pd.DataFrame([{"game_id": "GAME1"}, {"game_id": "GAME2"}])
        paths = collector.save_game_pages(games, tmp_path, limit=1)
    finally:
        data_sources.fetch_text = original

    assert paths == [tmp_path / "GAME1_game.html"]
    assert fetched[0][0] == "https://example.test/game/?GameID=GAME1"


def test_standardize_mykbo_tables_writes_named_outputs(tmp_path):
    source = tmp_path / "tables"
    output = tmp_path / "out"
    source.mkdir()
    pd.DataFrame(
        [
            {
                "Rank / Player": "1 Austin Dean",
                "Team": "LG Twins",
                "OPS": 0.988,
                "BA": 0.313,
                "OBP": 0.393,
                "SLG": 0.595,
                "1B": 76,
                "2B": 25,
                "3B": 1,
                "HR": 31,
                "BB": 61,
                "HBP": 2,
                "AB": 425,
                "PA": 499,
            }
        ]
    ).to_csv(source / "batting_ops_2025_table_1.csv", index=False)
    pd.DataFrame([{"text": "Austin Dean", "href": "/players/2451-Austin-Dean-LG-Twins"}]).to_csv(
        source / "batting_ops_2025_links.csv",
        index=False,
    )
    pd.DataFrame(
        [
            {
                "Rank / Player": "1 Cody Ponce",
                "Team": "Hanwha Eagles",
                "ERA": 1.89,
                "WHIP": 0.94,
                "IP": "180 &frac23;",
                "ER": 38,
                "R": 41,
                "H": 128,
                "HR": 10,
                "BB": 41,
                "HB": 6,
            }
        ]
    ).to_csv(source / "pitching_era_2025_table_1.csv", index=False)
    pd.DataFrame([{"text": "Cody Ponce", "href": "/players/3000-Cody-Ponce-Hanwha-Eagles"}]).to_csv(
        source / "pitching_era_2025_links.csv",
        index=False,
    )
    pd.DataFrame([{"Season": "LG Twins", "G": 144, "W": 85}]).to_csv(source / "team_splits_2025_table_1.csv", index=False)
    pd.DataFrame([["Games", "720"]]).to_csv(source / "stats_2025_table_1.csv", index=False)

    outputs = standardize_mykbo_tables(source, output, season=2025)
    batting = pd.read_csv(outputs["batting_season"])
    pitching = pd.read_csv(outputs["pitching_season"])
    teams = pd.read_csv(outputs["team_splits"])

    assert batting.loc[0, "player_name"] == "Austin Dean"
    assert batting.loc[0, "mykbo_player_id"] == 2451
    assert abs(pitching.loc[0, "IP"] - (180 + 2 / 3)) < 1e-9
    assert pitching.loc[0, "hit_by_pitch"] == 6
    assert teams.loc[0, "team"] == "LG Twins"


def test_standardize_proeyekyuu_tables_writes_named_outputs(tmp_path):
    source = tmp_path / "tables"
    output = tmp_path / "out"
    source.mkdir()
    pd.DataFrame(
        [
            {
                "Season": 2026,
                "Name": "Suzuki, Kyo",
                "PlayerID": "01005159",
                "Team": "Swallows",
                "Game Type": "Reg Season",
                "Position": "C",
                "PA": 61,
                "AB": 59,
                "OBP": 0.246,
                "SLG": 0.373,
                "OPS": 0.619,
                "HR": 1,
                "BB": 2,
                "K": 11,
            },
            {
                "Season": 2025,
                "Name": "Old Row",
                "PlayerID": "00000001",
                "Team": "Swallows",
                "Game Type": "Reg Season",
                "Position": "C",
                "PA": 1,
            },
        ]
    ).to_csv(source / "player_batting_stats_table_1.csv", index=False)
    pd.DataFrame(
        [
            {
                "Season": 2026,
                "League": "Central",
                "Team": "Swallows",
                "Game Type": "Reg Season",
                "G": 39,
                "PA": "1,400",
                "HR": 28,
            }
        ]
    ).to_csv(source / "team_batting_stats_table_1.csv", index=False)

    outputs = standardize_proeyekyuu_tables(source, output, season=2026)
    batting = pd.read_csv(outputs["batting_season"])
    teams = pd.read_csv(outputs["team_batting_season"])

    assert batting.shape[0] == 1
    assert batting.loc[0, "player_name"] == "Suzuki, Kyo"
    assert batting.loc[0, "player_id"] == 1005159
    assert batting.loc[0, "plate_appearances"] == 61
    assert teams.loc[0, "team"] == "Swallows"
    assert teams.loc[0, "plate_appearances"] == 1400


def test_standardize_proeyekyuu_game_results_writes_games(tmp_path):
    source = tmp_path / "tables"
    source.mkdir()
    pd.DataFrame(
        [
            {
                "GameID": "GAME20260327DBYS0003",
                "Season": 2026,
                "Date": "2026-03-27",
                "Game Type": "Reg Season",
                "Team": "Tokyo Yakult Swallows",
                "Home or Away": "Away",
                "Result": "W",
                "Score": 3,
                "Other Team": "Yokohama DeNA Baystars",
                "Ballpark": "Yokohama Stadium",
            },
            {
                "GameID": "GAME20260327DBYS0003",
                "Season": 2026,
                "Date": "2026-03-27",
                "Game Type": "Reg Season",
                "Team": "Yokohama DeNA Baystars",
                "Home or Away": "Home",
                "Result": "L",
                "Score": 2,
                "Other Team": "Tokyo Yakult Swallows",
                "Ballpark": "Yokohama Stadium",
            },
        ]
    ).to_csv(source / "game_results_table_1.csv", index=False)

    path = standardize_proeyekyuu_game_results(source, tmp_path / "games.csv")
    games = pd.read_csv(path)

    assert games.loc[0, "game_id"] == "GAME20260327DBYS0003"
    assert games.loc[0, "home_team"] == "Yokohama DeNA Baystars"
    assert games.loc[0, "away_team"] == "Tokyo Yakult Swallows"
    assert games.loc[0, "home_score"] == 2
    assert games.loc[0, "away_score"] == 3
    assert games.loc[0, "venue_name"] == "Yokohama Stadium"
    assert games.loc[0, "source_href"] == "https://proeyekyuu.com/game/?GameID=GAME20260327DBYS0003"


def test_standardize_proeyekyuu_game_tables_writes_logs(tmp_path):
    source = tmp_path / "game_tables"
    output = tmp_path / "out"
    source.mkdir()
    games = pd.DataFrame(
        [
            {
                "game_id": "GAME1",
                "game_date": "2026-03-27",
                "season": 2026,
                "home_team": "Home Stars",
                "away_team": "Away Swallows",
            }
        ]
    )
    games_path = tmp_path / "games.csv"
    games.to_csv(games_path, index=False)
    pd.DataFrame(
        [
            {"text": "Away Batter", "href": "https://proeyekyuu.com/player/?PlayerID=101"},
            {"text": "Home Batter", "href": "https://proeyekyuu.com/player/?PlayerID=201"},
            {"text": "Away Starter", "href": "https://proeyekyuu.com/player/?PlayerID=301"},
            {"text": "Home Starter", "href": "https://proeyekyuu.com/player/?PlayerID=401"},
        ]
    ).to_csv(source / "GAME1_game_links.csv", index=False)
    pd.DataFrame(
        [
            {"GameID": "GAME1", "Pitcher": "Away Starter", "NP": 93, "BF": 21, "IP": "5.1", "H": 5, "HR": 1, "BB": 0, "DB": 0, "K": 7, "R": 2, "ER": 2, "Index": 0},
        ]
    ).to_csv(source / "GAME1_game_table_1.csv", index=False)
    pd.DataFrame(
        [
            {"GameID": "GAME1", "Pitcher": "Home Starter", "NP": 100, "BF": 26, "IP": "6", "H": 4, "HR": 2, "BB": 4, "DB": 0, "K": 7, "R": 3, "ER": 3, "Index": 0},
        ]
    ).to_csv(source / "GAME1_game_table_2.csv", index=False)
    pd.DataFrame(
        [
            {"GameID": "GAME1", "Order": 1, "Pos": "CF", "Batter": "Away Batter", "AB": 4, "R": 1, "H": 2, "RBI": 0, "SB": 0, "Index": 0},
        ]
    ).to_csv(source / "GAME1_game_table_3.csv", index=False)
    pd.DataFrame(
        [
            {"GameID": "GAME1", "Order": 1, "Pos": "2B", "Batter": "Home Batter", "AB": 4, "R": 2, "H": 2, "RBI": 1, "SB": 0, "Index": 0},
        ]
    ).to_csv(source / "GAME1_game_table_4.csv", index=False)

    outputs = standardize_proeyekyuu_game_tables(source, games_path, output)
    batting = pd.read_csv(outputs["batting_logs"])
    pitching = pd.read_csv(outputs["pitcher_logs"])
    lineups = pd.read_csv(outputs["lineups"])

    assert batting.loc[0, "team"] == "Away Swallows"
    assert batting.loc[0, "player_id"] == 101
    assert batting.loc[0, "plate_appearances"] == 4
    assert pitching.loc[0, "team"] == "Away Swallows"
    assert pitching.loc[0, "innings_pitched"] == 5 + 1 / 3
    assert pitching.loc[0, "is_start"] == 1
    assert lineups.loc[0, "lineup_source"] == "proeyekyuu_game_page"


def test_standardize_proeyekyuu_game_tables_accepts_plus_ip_marker(tmp_path):
    source = tmp_path / "game_tables"
    output = tmp_path / "out"
    source.mkdir()
    pd.DataFrame(
        [{"game_id": "GAME1", "game_date": "2026-03-27", "season": 2026, "home_team": "Home Stars", "away_team": "Away Swallows"}]
    ).to_csv(tmp_path / "games.csv", index=False)
    pd.DataFrame([{"text": "Away Opener", "href": "https://proeyekyuu.com/player/?PlayerID=301"}]).to_csv(
        source / "GAME1_game_links.csv",
        index=False,
    )
    pd.DataFrame(
        [{"GameID": "GAME1", "Pitcher": "Away Opener", "NP": 3, "BF": 1, "IP": "0+", "H": 1, "HR": 0, "BB": 0, "DB": 0, "K": 0, "R": 1, "ER": 1, "Index": 0}]
    ).to_csv(source / "GAME1_game_table_1.csv", index=False)

    outputs = standardize_proeyekyuu_game_tables(source, tmp_path / "games.csv", output)
    pitching = pd.read_csv(outputs["pitcher_logs"])

    assert pitching.loc[0, "innings_pitched"] == 0.0


def test_write_proeyekyuu_games_with_starters_fills_game_backbone(tmp_path):
    games = pd.DataFrame(
        [
            {
                "game_id": "GAME1",
                "game_date": "2026-03-27",
                "season": 2026,
                "home_team": "Home Stars",
                "away_team": "Away Swallows",
                "home_sp_id": pd.NA,
                "away_sp_id": pd.NA,
            }
        ]
    )
    games_path = tmp_path / "games.csv"
    games.to_csv(games_path, index=False)
    pitcher_logs = pd.DataFrame(
        [
            {"game_id": "GAME1", "team": "Away Swallows", "player_id": "301", "player_name": "Away Starter", "is_start": 1, "innings_pitched": 5.0},
            {"game_id": "GAME1", "team": "Away Swallows", "player_id": "302", "player_name": "Away Reliever", "is_start": 0, "innings_pitched": 1.0},
            {"game_id": "GAME1", "team": "Home Stars", "player_id": "401", "player_name": "Home Starter", "is_start": 1, "innings_pitched": 6.0},
        ]
    )
    pitcher_logs_path = tmp_path / "pitcher_logs.csv"
    pitcher_logs.to_csv(pitcher_logs_path, index=False)

    path = write_proeyekyuu_games_with_starters(games_path, pitcher_logs_path, tmp_path / "games_with_starters.csv")
    out = pd.read_csv(path, dtype={"home_sp_id": str, "away_sp_id": str})

    assert out.loc[0, "home_sp_id"] == "401"
    assert out.loc[0, "away_sp_id"] == "301"
    assert out.loc[0, "home_sp_name"] == "Home Starter"
    assert out.loc[0, "away_sp_name"] == "Away Starter"


def test_npb_venue_template_and_backfill(tmp_path):
    games = pd.DataFrame(
        [{"game_id": "GAME1", "venue_name": "Yokohama Stadium", "home_team": "Home", "away_team": "Away"}]
    )
    games_path = tmp_path / "games.csv"
    games.to_csv(games_path, index=False)

    template = write_npb_venue_template(games_path, tmp_path / "venues_template.csv")
    venues = pd.read_csv(template)
    assert venues.loc[0, "venue_id"] == "npb_yokohama_stadium"

    venues["latitude"] = 35.4433
    venues["longitude"] = 139.6401
    enriched = write_npb_games_with_venues(games_path, template, tmp_path / "games_with_venues.csv")
    out = pd.read_csv(enriched)

    assert out.loc[0, "venue_id"] == "npb_yokohama_stadium"
    assert "venue_latitude" in out.columns


def test_write_proeyekyuu_batting_detail_audit_reports_missing_events(tmp_path):
    source = tmp_path / "tables"
    source.mkdir()
    pd.DataFrame([{"GameID": "GAME1", "Batter": "Hitter", "AB": 4, "R": 1, "H": 2, "RBI": 1, "SB": 0}]).to_csv(
        source / "GAME1_game_table_1.csv",
        index=False,
    )

    path = write_proeyekyuu_batting_detail_audit(source, tmp_path / "audit.md")
    text = path.read_text(encoding="utf-8")

    assert "Parsed batting tables scanned: 1" in text
    assert "| `home_runs` | `HR` | missing |" in text


def test_write_npb_feature_set_excludes_statcast_tracking(tmp_path):
    features = pd.DataFrame(
        [
            {
                "game_id": "GAME1",
                "home_team_win": 1,
                "home_lineup_xwoba_proxy": 0.3,
                "home_sp_statcast_xwoba_allowed_to_date": None,
                "home_sp_avg_fastball_velocity_to_date": 95.0,
            }
        ]
    )
    features_path = tmp_path / "features.csv"
    features.to_csv(features_path, index=False)

    path = write_npb_feature_set(features_path, tmp_path / "feature_set.csv")
    out = pd.read_csv(path)

    assert out.loc[out["column"].eq("home_lineup_xwoba_proxy"), "status"].iloc[0] == "included"
    assert out.loc[out["column"].eq("home_sp_avg_fastball_velocity_to_date"), "reason"].iloc[0] == "mlb_only_tracking"


def test_write_npb_model_ready_features_keeps_only_included_public_columns(tmp_path):
    features = pd.DataFrame(
        [
            {
                "game_id": "GAME1",
                "season": 2026,
                "home_team_win": 1,
                "home_lineup_xwoba_proxy": 0.3,
                "home_sp_avg_fastball_velocity_to_date": 95.0,
            }
        ]
    )
    feature_set = pd.DataFrame(
        [
            {"column": "home_lineup_xwoba_proxy", "status": "included"},
            {"column": "home_sp_avg_fastball_velocity_to_date", "status": "excluded"},
        ]
    )
    features_path = tmp_path / "features.csv"
    feature_set_path = tmp_path / "feature_set.csv"
    features.to_csv(features_path, index=False)
    feature_set.to_csv(feature_set_path, index=False)

    path = write_npb_model_ready_features(features_path, feature_set_path, tmp_path / "model_ready.csv")
    out = pd.read_csv(path)

    assert "game_id" in out.columns
    assert "home_team_win" in out.columns
    assert "home_lineup_xwoba_proxy" in out.columns
    assert "home_sp_avg_fastball_velocity_to_date" not in out.columns


def test_write_proeyekyuu_coverage_report_summarizes_canonical_files(tmp_path):
    games = pd.DataFrame(
        [
            {"game_id": "GAME1", "game_date": "2026-03-27", "home_sp_id": "401", "away_sp_id": "301"},
            {"game_id": "GAME2", "game_date": "2026-03-28", "home_sp_id": "", "away_sp_id": ""},
        ]
    )
    games_path = tmp_path / "games.csv"
    games.to_csv(games_path, index=False)
    standard = tmp_path / "standard"
    standard.mkdir()
    pd.DataFrame(
        [
            {"game_id": "GAME1", "player_id": "101", "doubles": 0, "triples": 0, "home_runs": 0, "walks": 0, "hit_by_pitch": 0, "sacrifice_flies": 0},
            {"game_id": "GAME1", "player_id": "", "doubles": 0, "triples": 0, "home_runs": 0, "walks": 0, "hit_by_pitch": 0, "sacrifice_flies": 0},
        ]
    ).to_csv(standard / "batting_logs.csv", index=False)
    pd.DataFrame(
        [
            {"game_id": "GAME1", "player_id": "301", "is_start": 1},
            {"game_id": "GAME1", "player_id": "401", "is_start": 1},
        ]
    ).to_csv(standard / "pitcher_logs.csv", index=False)
    pd.DataFrame(
        [{"game_id": "GAME1", "player_id": str(100 + index)} for index in range(18)]
    ).to_csv(standard / "lineups.csv", index=False)

    report = write_proeyekyuu_coverage_report(games_path, standard, tmp_path / "coverage.md")
    text = report.read_text(encoding="utf-8")

    assert "| Scheduled games | 2 |" in text
    assert "| Canonical game coverage | 1 (50.0%) |" in text
    assert "| Games with home starter ID | 1 (50.0%) |" in text
    assert "| Games with away starter ID | 1 (50.0%) |" in text
    assert "| Games with at least 18 lineup rows | 1 |" in text
    assert "Statcast and pitch-level features remain unavailable" in text


def test_standardize_mykbo_schedule_links_writes_games(tmp_path):
    source = tmp_path / "schedule"
    source.mkdir()
    pd.DataFrame(
        [
            {"text": "LG Twins 5 : 9 Final KT Wiz", "href": "/games/12367-LG-vs-KT-20250402"},
            {"text": "Kia Tigers Canceled Rained Out LG Twins", "href": "/games/12383-Kia-vs-LG-20250405"},
            {"text": "Hanwha Eagles 0 : 3 Bot 9th LG Twins", "href": "/games/13352-Hanwha-vs-LG-20260422"},
            {"text": "KT Wiz 6:30pm Seoul-Jamsil Doosan Bears", "href": "/games/13509-KT-vs-Doosan-20260528"},
            {"text": "Schedule", "href": "/schedule"},
        ]
    ).to_csv(source / "schedule_week_of_2025-04-05_links.csv", index=False)

    path = standardize_mykbo_schedule_links(source, tmp_path / "games.csv")
    games = pd.read_csv(path)

    assert len(games) == 4
    assert games.loc[0, "game_id"] == 12367
    assert games.loc[0, "away_team"] == "LG Twins"
    assert games.loc[0, "home_team"] == "KT Wiz"
    assert games.loc[0, "away_score"] == 5
    assert games.loc[0, "home_team_win"] == 1
    assert games.loc[1, "is_canceled"] == 1
    assert games.loc[1, "cancel_reason"] == "Rained Out"
    assert games.loc[2, "is_live"] == 1
    assert games.loc[2, "status"] == "Bot 9th"
    assert games.loc[3, "status"] == "Scheduled"
    assert games.loc[3, "scheduled_time"] == "6:30pm"
    assert games.loc[3, "venue_name"] == "Seoul-Jamsil"


def test_mykbo_save_game_pages_fetches_game_hrefs(tmp_path):
    collector = MyKBOStatsCollector(base_url="https://example.test")
    fetched = []

    def fake_fetch_url(url):
        fetched.append(url)
        return "<html><main>Game</main></html>"

    collector.fetch_url = fake_fetch_url
    games = pd.DataFrame(
        [
            {"game_id": "1", "source_href": "/games/1-A-vs-B-20250401"},
            {"game_id": "2", "source_href": "/teams/1"},
            {"game_id": "3", "source_href": "/games/3-C-vs-D-20250402"},
        ]
    )

    paths = collector.save_game_pages(games, tmp_path, limit=1)

    assert len(paths) == 1
    assert paths[0] == tmp_path / "1_game.html"
    assert paths[0].exists()
    assert fetched == ["https://example.test/games/1-A-vs-B-20250401"]


def test_standardize_mykbo_game_tables_writes_logs(tmp_path):
    source = tmp_path / "game_tables"
    output = tmp_path / "out"
    source.mkdir()
    games = pd.DataFrame({"game_id": ["1"], "game_date": ["2025-04-01"], "season": [2025]})
    games_path = tmp_path / "games.csv"
    games.to_csv(games_path, index=False)
    pd.DataFrame(
        [
            {"text": "Player One", "href": "/players/10-Player-One-LG-Twins"},
            {"text": "Pitcher One", "href": "/players/20-Pitcher-One-LG-Twins"},
        ]
    ).to_csv(source / "1_game_links.csv", index=False)
    pd.DataFrame(
        [
            {"LG": "1 Player One  #7", "Pos": "CF", "BA": 0.300, "AB": 4, "R": 1, "H": 2, "HR": 1, "RBI": 2, "BB": 1, "SO": 0, "HBP": 0}
        ]
    ).to_csv(source / "1_game_table_1.csv", index=False)
    pd.DataFrame(
        [
            {"KT": "1 Player Two  #8", "Pos": "SS", "BA": 0.250, "AB": 3, "R": 0, "H": 1, "HR": 0, "RBI": 0, "BB": 0, "SO": 1, "HBP": 0}
        ]
    ).to_csv(source / "1_game_table_2.csv", index=False)
    pd.DataFrame(
        [
            {"LG": "Pitcher One  #20", "ERA": 2.0, "IP": "5 &frac23;", "NP": 90, "R": 1, "ER": 1, "H": 5, "HR": 0, "SO": 6, "BB": 2, "HB": 0, "GS": 55}
        ]
    ).to_csv(source / "1_game_table_3.csv", index=False)
    pd.DataFrame(
        [
            {"KT": "Pitcher Two  #30", "ERA": 3.0, "IP": "4", "NP": 80, "R": 3, "ER": 3, "H": 6, "HR": 1, "SO": 3, "BB": 1, "HB": 0, "GS": 40}
        ]
    ).to_csv(source / "1_game_table_4.csv", index=False)

    outputs = standardize_mykbo_game_tables(source, games_path, output)
    batting = pd.read_csv(outputs["batting_logs"])
    pitching = pd.read_csv(outputs["pitcher_logs"])
    lineups = pd.read_csv(outputs["lineups"])

    assert batting.loc[0, "player_name"] == "Player One"
    assert batting.loc[0, "team"] == "LG Twins"
    assert batting.loc[0, "mykbo_player_id"] == 10
    assert pitching.loc[0, "innings_pitched"] == 5 + 2 / 3
    assert pitching.loc[0, "is_start"] == 1
    assert lineups.loc[0, "prediction_mode"] == "confirmed_lineup"


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


def test_balldontlie_lineups_fetches_paginated_payload(monkeypatch):
    import mlb_winprob.data_sources as data_sources

    calls = []

    def fake_fetch_json(url, params=None, *, headers=None):
        calls.append((url, dict(params or {}), dict(headers or {})))
        if len(calls) == 1:
            return {"data": [{"id": "lineup-1"}], "meta": {"next_cursor": "abc"}}
        return {"data": [{"id": "lineup-2"}], "meta": {}}

    monkeypatch.setattr(data_sources, "fetch_json", fake_fetch_json)

    payload = BallDontLieMLBCollector(api_key="test-key").lineups(game_ids=[10, 20], dates=["2026-05-26"])

    assert payload["data"] == [{"id": "lineup-1"}, {"id": "lineup-2"}]
    assert calls[0][0] == "https://api.balldontlie.io/mlb/v1/lineups"
    assert calls[0][1]["game_ids[]"] == ["10", "20"]
    assert calls[0][1]["dates[]"] == ["2026-05-26"]
    assert calls[0][2]["Authorization"] == "test-key"
    assert calls[1][1]["cursor"] == "abc"


def test_normalize_balldontlie_lineups_maps_to_standard_schema():
    payload = {
        "data": [
            {
                "game": {"id": 9001},
                "team": {"abbreviation": "NYY"},
                "status": "projected",
                "players": [
                    {
                        "player": {"id": 101, "full_name": "Leadoff Hitter", "bats": "L"},
                        "batting_order": 1,
                        "position": "CF",
                    },
                    {
                        "player": {"id": 102, "full_name": "Second Hitter", "bats": "R"},
                        "batting_order": 2,
                        "position": "SS",
                    },
                ],
            }
        ]
    }
    game_map = pd.DataFrame({"external_game_id": [9001], "game_id": ["mlb-1"]})
    player_map = pd.DataFrame({"external_player_id": [101, 102], "player_id": [501, 502]})

    frame = BallDontLieMLBCollector.normalize_lineups(
        payload,
        captured_at="2026-05-26T10:00:00Z",
        game_id_map=game_map,
        player_id_map=player_map,
    )

    assert len(frame) == 2
    assert frame["game_id"].tolist() == ["mlb-1", "mlb-1"]
    assert frame["team"].tolist() == ["NYY", "NYY"]
    assert frame["player_id"].tolist() == [501, 502]
    assert frame["batting_order"].tolist() == [1, 2]
    assert frame["prediction_mode"].tolist() == ["projected", "projected"]
    assert frame["lineup_source"].tolist() == ["balldontlie_mlb", "balldontlie_mlb"]
    assert frame["captured_at"].tolist() == ["2026-05-26T10:00:00Z", "2026-05-26T10:00:00Z"]
    assert frame["external_game_id"].tolist() == [9001, 9001]
    assert frame["external_player_id"].tolist() == [101, 102]
