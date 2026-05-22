"""Aggregate Baseball Savant / Statcast events into game-player logs."""

from __future__ import annotations

import numpy as np
import pandas as pd


def _numeric_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype="float64")
    return pd.to_numeric(frame[column], errors="coerce")


def _object_column(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(pd.NA, index=frame.index, dtype="object")
    return frame[column]


def _team_from_half_inning(frame: pd.DataFrame, *, batting: bool) -> pd.Series:
    top = frame["inning_topbot"].astype(str).str.lower().eq("top")
    if batting:
        return np.where(top, frame["away_team"], frame["home_team"])
    return np.where(top, frame["home_team"], frame["away_team"])


def _barrel_mask(frame: pd.DataFrame) -> pd.Series:
    if "launch_speed_angle" in frame.columns:
        return pd.to_numeric(frame["launch_speed_angle"], errors="coerce").eq(6)
    launch_speed = _numeric_column(frame, "launch_speed")
    launch_angle = _numeric_column(frame, "launch_angle")
    return launch_speed.ge(98) & launch_angle.between(26, 30)


def _prepare_statcast_events(events: pd.DataFrame) -> pd.DataFrame:
    required = ["game_pk", "game_date", "batter", "pitcher", "home_team", "away_team", "inning_topbot"]
    missing = [column for column in required if column not in events.columns]
    if missing:
        raise ValueError(f"statcast events is missing required columns: {missing}")

    out = events.copy()
    out["game_id"] = out["game_pk"].astype(str)
    out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce")
    out["season"] = out["game_date"].dt.year
    out["batter_team"] = _team_from_half_inning(out, batting=True)
    out["pitcher_team"] = _team_from_half_inning(out, batting=False)
    out["is_pa"] = out.get("events", pd.Series(index=out.index, dtype="object")).notna()
    out["is_batted_ball"] = (
        _numeric_column(out, "launch_speed").notna()
        | _numeric_column(out, "launch_angle").notna()
        | _object_column(out, "bb_type").notna()
    )
    out["is_hard_hit"] = _numeric_column(out, "launch_speed").ge(95) & out["is_batted_ball"]
    out["is_barrel"] = _barrel_mask(out) & out["is_batted_ball"]
    out["is_whiff"] = _object_column(out, "description").astype(str).isin(
        ["swinging_strike", "swinging_strike_blocked", "foul_tip"]
    )
    out["woba_value_numeric"] = _numeric_column(out, "woba_value")
    out["xwoba_numeric"] = _numeric_column(out, "estimated_woba_using_speedangle")
    out["launch_speed_numeric"] = _numeric_column(out, "launch_speed")
    out["release_speed_numeric"] = _numeric_column(out, "release_speed")
    out["release_spin_rate_numeric"] = _numeric_column(out, "release_spin_rate")
    out["pitch_type_normalized"] = _object_column(out, "pitch_type").astype(str).str.upper()
    return out


def aggregate_statcast_batting(events: pd.DataFrame) -> pd.DataFrame:
    """Return batter game-level Statcast quality sums suitable for feature building."""

    prepared = _prepare_statcast_events(events)
    prepared["player_id"] = prepared["batter"]
    prepared["team"] = prepared["batter_team"]
    if "p_throws" in prepared.columns:
        prepared["opposing_pitcher_hand"] = prepared["p_throws"].astype(str).str.upper().str[0]
    else:
        prepared["opposing_pitcher_hand"] = np.nan
    return _aggregate_player_quality(prepared, ["game_id", "game_date", "season", "player_id", "team"])


def aggregate_statcast_pitching(events: pd.DataFrame) -> pd.DataFrame:
    """Return pitcher game-level Statcast quality sums allowed."""

    prepared = _prepare_statcast_events(events)
    prepared["player_id"] = prepared["pitcher"]
    prepared["team"] = prepared["pitcher_team"]
    aggregated = _aggregate_player_quality(prepared, ["game_id", "game_date", "season", "player_id", "team"])
    return aggregated.rename(
        columns={
            "statcast_pa": "statcast_batters_faced",
            "statcast_xwoba_sum": "statcast_xwoba_allowed_sum",
            "statcast_xwoba_count": "statcast_xwoba_allowed_count",
            "statcast_woba_sum": "statcast_woba_allowed_sum",
            "statcast_woba_count": "statcast_woba_allowed_count",
            "statcast_batted_balls": "statcast_batted_balls_allowed",
            "statcast_hard_hit_balls": "statcast_hard_hit_balls_allowed",
            "statcast_barrels": "statcast_barrels_allowed",
            "statcast_launch_speed_sum": "statcast_launch_speed_allowed_sum",
        }
    )


def _aggregate_player_quality(prepared: pd.DataFrame, group_columns: list[str]) -> pd.DataFrame:
    work = prepared.copy()
    work["statcast_pa"] = work["is_pa"].astype(int)
    work["statcast_batted_balls"] = work["is_batted_ball"].astype(int)
    work["statcast_hard_hit_balls"] = work["is_hard_hit"].astype(int)
    work["statcast_barrels"] = work["is_barrel"].astype(int)
    work["statcast_whiffs"] = work["is_whiff"].astype(int)
    work["statcast_pitches"] = 1
    work["statcast_xwoba_sum"] = work["xwoba_numeric"].fillna(0.0)
    work["statcast_xwoba_count"] = work["xwoba_numeric"].notna().astype(int)
    work["statcast_woba_sum"] = work["woba_value_numeric"].fillna(0.0)
    work["statcast_woba_count"] = work["woba_value_numeric"].notna().astype(int)
    work["statcast_launch_speed_sum"] = work["launch_speed_numeric"].where(work["is_batted_ball"], 0.0).fillna(0.0)
    work["statcast_release_speed_sum"] = work["release_speed_numeric"].fillna(0.0)
    work["statcast_release_speed_count"] = work["release_speed_numeric"].notna().astype(int)
    fastball = work["pitch_type_normalized"].isin(["FF", "SI", "FC"])
    work["statcast_fastball_release_speed_sum"] = work["release_speed_numeric"].where(fastball, 0.0).fillna(0.0)
    work["statcast_fastball_release_speed_count"] = (work["release_speed_numeric"].notna() & fastball).astype(int)
    work["statcast_spin_rate_sum"] = work["release_spin_rate_numeric"].fillna(0.0)
    work["statcast_spin_rate_count"] = work["release_spin_rate_numeric"].notna().astype(int)
    for pitch_type in ["FF", "SI", "FC", "SL", "CU", "CH", "FS"]:
        work[f"statcast_pitch_{pitch_type.lower()}"] = work["pitch_type_normalized"].eq(pitch_type).astype(int)
    aggregate_columns = [
        "statcast_pa",
        "statcast_batted_balls",
        "statcast_hard_hit_balls",
        "statcast_barrels",
        "statcast_whiffs",
        "statcast_pitches",
        "statcast_xwoba_sum",
        "statcast_xwoba_count",
        "statcast_woba_sum",
        "statcast_woba_count",
        "statcast_launch_speed_sum",
        "statcast_release_speed_sum",
        "statcast_release_speed_count",
        "statcast_fastball_release_speed_sum",
        "statcast_fastball_release_speed_count",
        "statcast_spin_rate_sum",
        "statcast_spin_rate_count",
        "statcast_pitch_ff",
        "statcast_pitch_si",
        "statcast_pitch_fc",
        "statcast_pitch_sl",
        "statcast_pitch_cu",
        "statcast_pitch_ch",
        "statcast_pitch_fs",
    ]
    return work.groupby(group_columns, as_index=False)[aggregate_columns].sum()


def merge_statcast_quality(
    *,
    batting_logs: pd.DataFrame,
    pitcher_logs: pd.DataFrame,
    statcast_batting: pd.DataFrame,
    statcast_pitching: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge aggregated Statcast quality columns into standard logs."""

    batting_keys = ["game_id", "player_id", "team"]
    pitching_keys = ["game_id", "player_id", "team"]
    batting = batting_logs.copy()
    pitching = pitcher_logs.copy()
    for frame in [batting, pitching, statcast_batting, statcast_pitching]:
        for column in ["game_id", "player_id", "team"]:
            if column in frame.columns:
                frame[column] = frame[column].astype(str)
    batting_quality_columns = [column for column in statcast_batting.columns if column.startswith("statcast_")]
    pitching_quality_columns = [column for column in statcast_pitching.columns if column.startswith("statcast_")]
    batting = batting.merge(
        statcast_batting[[*batting_keys, *batting_quality_columns]],
        on=batting_keys,
        how="left",
    )
    pitching = pitching.merge(
        statcast_pitching[[*pitching_keys, *pitching_quality_columns]],
        on=pitching_keys,
        how="left",
    )
    return batting, pitching
