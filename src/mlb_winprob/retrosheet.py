"""Standardize Retrosheet CSV tables into the project schema."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import write_csv_table


GAMEINFO_COLUMNS = [
    "gid",
    "visteam",
    "hometeam",
    "site",
    "date",
    "starttime",
    "daynight",
    "gametype",
    "vruns",
    "hruns",
    "fieldcond",
    "precip",
    "sky",
    "temp",
    "winddir",
    "windspeed",
    "season",
]
TEAMSTATS_COLUMNS = [
    "gid",
    "team",
    "stattype",
    "date",
    "vishome",
    "opp",
    "gametype",
    *[f"start_l{i}" for i in range(1, 10)],
]
BATTING_COLUMNS = [
    "gid",
    "id",
    "team",
    "b_lp",
    "stattype",
    "b_pa",
    "b_ab",
    "b_r",
    "b_h",
    "b_d",
    "b_t",
    "b_hr",
    "b_rbi",
    "b_sh",
    "b_sf",
    "b_hbp",
    "b_w",
    "b_iw",
    "b_k",
    "b_sb",
    "b_cs",
    "b_gdp",
    "date",
    "vishome",
    "opp",
    "gametype",
]
PITCHING_COLUMNS = [
    "gid",
    "id",
    "team",
    "p_seq",
    "stattype",
    "p_ipouts",
    "p_bfp",
    "p_h",
    "p_hr",
    "p_r",
    "p_er",
    "p_w",
    "p_iw",
    "p_k",
    "p_hbp",
    "p_wp",
    "p_bk",
    "p_sh",
    "p_sf",
    "save",
    "p_gs",
    "p_gf",
    "p_cg",
    "date",
    "vishome",
    "opp",
    "gametype",
]


def _read_retrosheet(path: str | Path, columns: list[str], seasons: list[int] | None = None) -> pd.DataFrame:
    frame = pd.read_csv(path, usecols=columns, low_memory=False)
    if "date" in frame.columns:
        numeric_date = pd.to_numeric(frame["date"], errors="coerce")
        if seasons is not None:
            min_date = min(seasons) * 10000
            max_date = max(seasons) * 10000 + 1231
            frame = frame[numeric_date.between(min_date, max_date)].copy()
            numeric_date = pd.to_numeric(frame["date"], errors="coerce")
        frame["game_date"] = pd.to_datetime(numeric_date.astype("Int64").astype(str), format="%Y%m%d", errors="coerce")
        frame["season"] = frame["game_date"].dt.year
        if seasons is not None:
            frame = frame[frame["season"].isin(seasons)].copy()
    return frame


def _regular_value_rows(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "stattype" in out.columns:
        out = out[out["stattype"].eq("value")].copy()
    if "gametype" in out.columns:
        out = out[out["gametype"].eq("regular")].copy()
    return out


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index)
    return pd.to_numeric(frame[column], errors="coerce")


def standardize_retrosheet_games(
    gameinfo: pd.DataFrame,
    pitching: pd.DataFrame,
) -> pd.DataFrame:
    games = _regular_value_rows(gameinfo)
    starters = pitching[pitching["p_gs"].fillna(0).astype(float).eq(1)].copy()
    home_starters = starters[starters["vishome"].eq("h")][["gid", "id"]].rename(columns={"id": "home_sp_id"})
    away_starters = starters[starters["vishome"].eq("v")][["gid", "id"]].rename(columns={"id": "away_sp_id"})
    games = games.merge(home_starters, on="gid", how="left").merge(away_starters, on="gid", how="left")
    out = pd.DataFrame(
        {
            "game_id": games["gid"],
            "game_date": games["game_date"],
            "season": games["season"],
            "home_team": games["hometeam"],
            "away_team": games["visteam"],
            "home_sp_id": games["home_sp_id"],
            "away_sp_id": games["away_sp_id"],
            "venue_id": games["site"],
            "home_score": _numeric(games, "hruns"),
            "away_score": _numeric(games, "vruns"),
            "prediction_mode": "confirmed_lineup",
        }
    )
    out["home_team_win"] = (out["home_score"] > out["away_score"]).astype(int)
    return out.sort_values(["game_date", "game_id"]).reset_index(drop=True)


def standardize_retrosheet_weather(gameinfo: pd.DataFrame) -> pd.DataFrame:
    games = _regular_value_rows(gameinfo)
    temp = _numeric(games, "temp")
    temp = temp.where(temp > 0)
    wind_speed = _numeric(games, "windspeed")
    wind_speed = wind_speed.where(wind_speed >= 0)
    condition = (
        games[["sky", "precip", "fieldcond"]]
        .fillna("")
        .astype(str)
        .agg("; ".join, axis=1)
        .str.replace(r"(unknown;?\s*)+", "", regex=True)
        .str.strip("; ")
    )
    out = pd.DataFrame(
        {
            "game_id": games["gid"],
            "temperature": temp,
            "wind_speed": wind_speed,
            "wind_direction": games["winddir"].replace({"unknown": np.nan}),
            "humidity": np.nan,
            "is_dome": games["sky"].astype(str).str.lower().str.contains("dome|indoor").astype(int),
            "weather_condition": condition.replace({"": np.nan}),
            "weather_source": "retrosheet",
        }
    )
    return out.reset_index(drop=True)


def standardize_retrosheet_lineups(teamstats: pd.DataFrame) -> pd.DataFrame:
    teams = _regular_value_rows(teamstats)
    rows: list[dict[str, object]] = []
    for _, row in teams.iterrows():
        for order in range(1, 10):
            player_id = row.get(f"start_l{order}")
            if pd.isna(player_id) or not str(player_id).strip():
                continue
            rows.append(
                {
                    "game_id": row["gid"],
                    "team": row["team"],
                    "player_id": str(player_id),
                    "batting_order": order,
                    "bats": np.nan,
                }
            )
    return pd.DataFrame(rows)


def standardize_retrosheet_batting(batting: pd.DataFrame) -> pd.DataFrame:
    value = _regular_value_rows(batting)
    out = pd.DataFrame(
        {
            "game_id": value["gid"],
            "game_date": value["game_date"],
            "season": value["season"],
            "team": value["team"],
            "player_id": value["id"],
            "batting_order": _numeric(value, "b_lp"),
            "plate_appearances": _numeric(value, "b_pa"),
            "at_bats": _numeric(value, "b_ab"),
            "runs": _numeric(value, "b_r"),
            "hits": _numeric(value, "b_h"),
            "doubles": _numeric(value, "b_d"),
            "triples": _numeric(value, "b_t"),
            "home_runs": _numeric(value, "b_hr"),
            "rbi": _numeric(value, "b_rbi"),
            "walks": _numeric(value, "b_w"),
            "intentional_walks": _numeric(value, "b_iw"),
            "strikeouts": _numeric(value, "b_k"),
            "hit_by_pitch": _numeric(value, "b_hbp"),
            "sacrifice_flies": _numeric(value, "b_sf"),
            "stolen_bases": _numeric(value, "b_sb"),
            "caught_stealing": _numeric(value, "b_cs"),
            "grounded_into_double_play": _numeric(value, "b_gdp"),
            "opposing_pitcher_hand": np.nan,
        }
    )
    out["total_bases"] = out["hits"] + out["doubles"] + 2 * out["triples"] + 3 * out["home_runs"]
    return out.sort_values(["game_date", "game_id", "team", "batting_order"]).reset_index(drop=True)


def standardize_retrosheet_pitching(pitching: pd.DataFrame) -> pd.DataFrame:
    value = _regular_value_rows(pitching)
    out = pd.DataFrame(
        {
            "game_id": value["gid"],
            "game_date": value["game_date"],
            "season": value["season"],
            "team": value["team"],
            "player_id": value["id"],
            "innings_pitched": _numeric(value, "p_ipouts") / 3.0,
            "games_started": _numeric(value, "p_gs"),
            "saves": _numeric(value, "save"),
            "holds": np.nan,
            "blown_saves": np.nan,
            "save_opportunities": np.nan,
            "games_finished": _numeric(value, "p_gf"),
            "complete_games": _numeric(value, "p_cg"),
            "hits": _numeric(value, "p_h"),
            "home_runs": _numeric(value, "p_hr"),
            "walks": _numeric(value, "p_w"),
            "intentional_walks": _numeric(value, "p_iw"),
            "hit_by_pitch": _numeric(value, "p_hbp"),
            "strikeouts": _numeric(value, "p_k"),
            "batters_faced": _numeric(value, "p_bfp"),
            "runs": _numeric(value, "p_r"),
            "earned_runs": _numeric(value, "p_er"),
            "wild_pitches": _numeric(value, "p_wp"),
            "balks": _numeric(value, "p_bk"),
            "pitches": np.nan,
        }
    )
    return out.sort_values(["game_date", "game_id", "team", "games_started"], ascending=[True, True, True, False]).reset_index(drop=True)


def standardize_retrosheet_tables(
    *,
    gameinfo_csv: str | Path,
    teamstats_csv: str | Path,
    batting_csv: str | Path,
    pitching_csv: str | Path,
    output_dir: str | Path,
    seasons: list[int] | None = None,
) -> dict[str, Path]:
    gameinfo = _read_retrosheet(gameinfo_csv, GAMEINFO_COLUMNS, seasons)
    teamstats = _read_retrosheet(teamstats_csv, TEAMSTATS_COLUMNS, seasons)
    batting = _read_retrosheet(batting_csv, BATTING_COLUMNS, seasons)
    pitching = _read_retrosheet(pitching_csv, PITCHING_COLUMNS, seasons)
    output = Path(output_dir)
    paths = {
        "games": output / "games.csv",
        "weather": output / "weather.csv",
        "lineups": output / "lineups.csv",
        "batting_logs": output / "batting_logs.csv",
        "pitcher_logs": output / "pitcher_logs.csv",
    }
    write_csv_table(standardize_retrosheet_games(gameinfo, _regular_value_rows(pitching)), paths["games"])
    write_csv_table(standardize_retrosheet_weather(gameinfo), paths["weather"])
    write_csv_table(standardize_retrosheet_lineups(teamstats), paths["lineups"])
    write_csv_table(standardize_retrosheet_batting(batting), paths["batting_logs"])
    write_csv_table(standardize_retrosheet_pitching(pitching), paths["pitcher_logs"])
    return paths
