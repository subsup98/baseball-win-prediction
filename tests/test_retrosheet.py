import pandas as pd

from mlb_winprob.retrosheet import (
    standardize_retrosheet_batting,
    standardize_retrosheet_games,
    standardize_retrosheet_lineups,
    standardize_retrosheet_pitching,
    standardize_retrosheet_weather,
)


def _gameinfo():
    return pd.DataFrame(
        [
            {
                "gid": "TST202404010",
                "visteam": "AWY",
                "hometeam": "HOM",
                "site": "PARK1",
                "game_date": pd.Timestamp("2024-04-01"),
                "season": 2024,
                "gametype": "regular",
                "vruns": 3,
                "hruns": 4,
                "fieldcond": "dry",
                "precip": "none",
                "sky": "night",
                "temp": 72,
                "winddir": "fromlf",
                "windspeed": 8,
            }
        ]
    )


def _pitching():
    return pd.DataFrame(
        [
            {
                "gid": "TST202404010",
                "id": "homep001",
                "team": "HOM",
                "stattype": "value",
                "game_date": pd.Timestamp("2024-04-01"),
                "season": 2024,
                "vishome": "h",
                "gametype": "regular",
                "p_ipouts": 18,
                "p_bfp": 24,
                "p_h": 5,
                "p_hr": 1,
                "p_r": 2,
                "p_er": 2,
                "p_w": 1,
                "p_iw": 0,
                "p_k": 7,
                "p_hbp": 0,
                "p_wp": 0,
                "p_bk": 0,
                "save": 0,
                "p_gs": 1,
                "p_gf": 0,
                "p_cg": 0,
            },
            {
                "gid": "TST202404010",
                "id": "awayp001",
                "team": "AWY",
                "stattype": "value",
                "game_date": pd.Timestamp("2024-04-01"),
                "season": 2024,
                "vishome": "v",
                "gametype": "regular",
                "p_ipouts": 15,
                "p_bfp": 23,
                "p_h": 6,
                "p_hr": 2,
                "p_r": 4,
                "p_er": 4,
                "p_w": 2,
                "p_iw": 0,
                "p_k": 5,
                "p_hbp": 1,
                "p_wp": 1,
                "p_bk": 0,
                "save": 0,
                "p_gs": 1,
                "p_gf": 0,
                "p_cg": 0,
            },
        ]
    )


def test_standardize_retrosheet_games_and_weather():
    games = standardize_retrosheet_games(_gameinfo(), _pitching())
    weather = standardize_retrosheet_weather(_gameinfo())

    assert games.loc[0, "home_sp_id"] == "homep001"
    assert games.loc[0, "away_sp_id"] == "awayp001"
    assert games.loc[0, "home_team_win"] == 1
    assert weather.loc[0, "temperature"] == 72
    assert weather.loc[0, "weather_source"] == "retrosheet"


def test_standardize_retrosheet_lineups_batting_and_pitching():
    teamstats = pd.DataFrame(
        [
            {
                "gid": "TST202404010",
                "team": "HOM",
                "stattype": "value",
                "gametype": "regular",
                **{f"start_l{i}": f"player{i}" for i in range(1, 10)},
            }
        ]
    )
    batting = pd.DataFrame(
        [
            {
                "gid": "TST202404010",
                "id": "player1",
                "team": "HOM",
                "b_lp": 1,
                "stattype": "value",
                "gametype": "regular",
                "game_date": pd.Timestamp("2024-04-01"),
                "season": 2024,
                "b_pa": 4,
                "b_ab": 3,
                "b_r": 1,
                "b_h": 2,
                "b_d": 1,
                "b_t": 0,
                "b_hr": 1,
                "b_rbi": 2,
                "b_sh": 0,
                "b_sf": 1,
                "b_hbp": 0,
                "b_w": 1,
                "b_iw": 0,
                "b_k": 1,
                "b_sb": 0,
                "b_cs": 0,
                "b_gdp": 0,
            }
        ]
    )

    lineups = standardize_retrosheet_lineups(teamstats)
    batting_logs = standardize_retrosheet_batting(batting)
    pitcher_logs = standardize_retrosheet_pitching(_pitching())

    assert len(lineups) == 9
    assert batting_logs.loc[0, "total_bases"] == 6
    assert pitcher_logs.loc[pitcher_logs["player_id"].eq("homep001"), "innings_pitched"].iloc[0] == 6
