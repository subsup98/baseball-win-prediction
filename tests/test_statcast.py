import pandas as pd

from mlb_winprob.statcast import aggregate_statcast_batting, aggregate_statcast_pitching, merge_statcast_quality


def _statcast_events():
    return pd.DataFrame(
        [
            {
                "game_pk": 1,
                "game_date": "2024-04-01",
                "batter": 10,
                "pitcher": 20,
                "home_team": "HOM",
                "away_team": "AWY",
                "inning_topbot": "Top",
                "events": "single",
                "description": "hit_into_play",
                "p_throws": "R",
                "launch_speed": 97,
                "launch_angle": 12,
                "launch_speed_angle": 3,
                "estimated_woba_using_speedangle": 0.43,
                "woba_value": 0.9,
            },
            {
                "game_pk": 1,
                "game_date": "2024-04-01",
                "batter": 10,
                "pitcher": 20,
                "home_team": "HOM",
                "away_team": "AWY",
                "inning_topbot": "Top",
                "events": "home_run",
                "description": "hit_into_play",
                "p_throws": "R",
                "launch_speed": 101,
                "launch_angle": 28,
                "launch_speed_angle": 6,
                "estimated_woba_using_speedangle": 1.8,
                "woba_value": 2.0,
            },
            {
                "game_pk": 1,
                "game_date": "2024-04-01",
                "batter": 11,
                "pitcher": 21,
                "home_team": "HOM",
                "away_team": "AWY",
                "inning_topbot": "Bot",
                "events": None,
                "description": "swinging_strike",
                "p_throws": "L",
                "launch_speed": None,
                "launch_angle": None,
                "estimated_woba_using_speedangle": None,
                "woba_value": None,
            },
        ]
    )


def test_aggregate_statcast_batting_quality():
    batting = aggregate_statcast_batting(_statcast_events())

    row = batting[(batting["game_id"] == "1") & (batting["player_id"] == 10)].iloc[0]
    assert row["team"] == "AWY"
    assert row["statcast_pa"] == 2
    assert row["statcast_batted_balls"] == 2
    assert row["statcast_hard_hit_balls"] == 2
    assert row["statcast_barrels"] == 1
    assert row["statcast_xwoba_sum"] == 2.23
    assert row["statcast_woba_sum"] == 2.9


def test_aggregate_statcast_pitching_quality():
    pitching = aggregate_statcast_pitching(_statcast_events())

    row = pitching[(pitching["game_id"] == "1") & (pitching["player_id"] == 20)].iloc[0]
    assert row["team"] == "HOM"
    assert row["statcast_batters_faced"] == 2
    assert row["statcast_batted_balls_allowed"] == 2
    assert row["statcast_barrels_allowed"] == 1
    assert row["statcast_xwoba_allowed_sum"] == 2.23


def test_merge_statcast_quality_into_standard_logs():
    batting_logs = pd.DataFrame([{"game_id": "1", "player_id": "10", "team": "AWY", "hits": 2}])
    pitcher_logs = pd.DataFrame([{"game_id": "1", "player_id": "20", "team": "HOM", "strikeouts": 1}])
    statcast_batting = aggregate_statcast_batting(_statcast_events())
    statcast_pitching = aggregate_statcast_pitching(_statcast_events())

    batting, pitching = merge_statcast_quality(
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        statcast_batting=statcast_batting,
        statcast_pitching=statcast_pitching,
    )

    assert batting.loc[0, "statcast_pa"] == 2
    assert pitching.loc[0, "statcast_batters_faced"] == 2
