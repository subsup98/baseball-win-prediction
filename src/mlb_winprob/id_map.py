"""Build player ID crosswalks from Chadwick Register and local metadata."""

from __future__ import annotations

from pathlib import Path
import re

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table


ID_MAP_COLUMNS = [
    "chadwick_key",
    "chadwick_uuid",
    "mlbam_id",
    "retrosheet_id",
    "bbref_id",
    "bbref_minors_id",
    "fangraphs_id",
    "wikidata_id",
    "name_first",
    "name_last",
    "name_given",
    "name_suffix",
    "birth_year",
    "birth_month",
    "birth_day",
    "mlb_played_first",
    "mlb_played_last",
    "bats",
    "throws",
    "primary_position",
]


def _clean_id(series: pd.Series) -> pd.Series:
    text = series.astype("string").str.strip()
    numeric = pd.to_numeric(text, errors="coerce")
    integer_like = numeric.notna() & (numeric % 1 == 0)
    text = text.mask(integer_like, numeric.astype("Int64").astype("string"))
    return text.replace({"": pd.NA, "<NA>": pd.NA, "nan": pd.NA, "None": pd.NA})


def build_id_map(chadwick_people: pd.DataFrame, mlb_people: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return an ID map with Chadwick, MLBAM, Retrosheet, BBRef, and FanGraphs IDs."""

    people = chadwick_people.copy()
    out = pd.DataFrame(
        {
            "chadwick_key": people.get("key_person"),
            "chadwick_uuid": people.get("key_uuid"),
            "mlbam_id": _clean_id(people.get("key_mlbam", pd.Series(index=people.index, dtype=object))),
            "retrosheet_id": _clean_id(people.get("key_retro", pd.Series(index=people.index, dtype=object))),
            "bbref_id": _clean_id(people.get("key_bbref", pd.Series(index=people.index, dtype=object))),
            "bbref_minors_id": _clean_id(people.get("key_bbref_minors", pd.Series(index=people.index, dtype=object))),
            "fangraphs_id": _clean_id(people.get("key_fangraphs", pd.Series(index=people.index, dtype=object))),
            "wikidata_id": _clean_id(people.get("key_wikidata", pd.Series(index=people.index, dtype=object))),
            "name_first": people.get("name_first"),
            "name_last": people.get("name_last"),
            "name_given": people.get("name_given"),
            "name_suffix": people.get("name_suffix"),
            "birth_year": pd.to_numeric(people.get("birth_year"), errors="coerce").astype("Int64"),
            "birth_month": pd.to_numeric(people.get("birth_month"), errors="coerce").astype("Int64"),
            "birth_day": pd.to_numeric(people.get("birth_day"), errors="coerce").astype("Int64"),
            "mlb_played_first": pd.to_numeric(people.get("mlb_played_first"), errors="coerce").astype("Int64"),
            "mlb_played_last": pd.to_numeric(people.get("mlb_played_last"), errors="coerce").astype("Int64"),
        }
    )
    out = out[
        out[["mlbam_id", "retrosheet_id", "bbref_id", "fangraphs_id"]].notna().any(axis=1)
    ].copy()

    if mlb_people is not None and not mlb_people.empty and "player_id" in mlb_people.columns:
        mlb = mlb_people.copy()
        mlb["mlbam_id"] = _clean_id(mlb["player_id"])
        keep_columns = ["mlbam_id"]
        for column in ["bats", "throws", "primary_position", "player_name"]:
            if column in mlb.columns:
                keep_columns.append(column)
        mlb = mlb[keep_columns].drop_duplicates("mlbam_id")
        out = out.merge(mlb, on="mlbam_id", how="left")
    else:
        out["bats"] = pd.NA
        out["throws"] = pd.NA
        out["primary_position"] = pd.NA

    for column in ["bats", "throws", "primary_position"]:
        if column not in out.columns:
            out[column] = pd.NA
    return out[ID_MAP_COLUMNS].sort_values(["mlb_played_last", "name_last", "name_first"], ascending=[False, True, True]).reset_index(drop=True)


def _normalize_name(value: object) -> str:
    text = "" if pd.isna(value) else str(value).lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    text = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _date_key(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce", utc=True).dt.date.astype("string")


def build_external_player_id_map(
    provider_lineups: pd.DataFrame,
    id_map: pd.DataFrame,
    *,
    season: int | None = None,
) -> pd.DataFrame:
    """Map provider player IDs to MLBAM IDs using normalized player names."""

    required = {"external_player_id", "player_name"}
    missing = required - set(provider_lineups.columns)
    if missing:
        raise ValueError(f"provider_lineups is missing columns: {sorted(missing)}")
    if "mlbam_id" not in id_map.columns:
        raise ValueError("id_map must contain mlbam_id")

    provider = provider_lineups[["external_player_id", "player_name"]].dropna().drop_duplicates().copy()
    provider["name_key"] = provider["player_name"].map(_normalize_name)

    candidates = id_map.copy()
    if season is not None and {"mlb_played_first", "mlb_played_last"}.issubset(candidates.columns):
        first = pd.to_numeric(candidates["mlb_played_first"], errors="coerce")
        last = pd.to_numeric(candidates["mlb_played_last"], errors="coerce")
        candidates = candidates[(first.isna() | (first <= season)) & (last.isna() | (last >= season))].copy()

    name_given = candidates.get("name_given", pd.Series(index=candidates.index, dtype=object))
    first_last = (
        candidates.get("name_first", pd.Series(index=candidates.index, dtype=object)).fillna("").astype(str)
        + " "
        + candidates.get("name_last", pd.Series(index=candidates.index, dtype=object)).fillna("").astype(str)
    )
    candidate_names = pd.concat(
        [
            pd.DataFrame({"mlbam_id": candidates["mlbam_id"], "matched_name": name_given}),
            pd.DataFrame({"mlbam_id": candidates["mlbam_id"], "matched_name": first_last}),
        ],
        ignore_index=True,
    )
    candidate_names["name_key"] = candidate_names["matched_name"].map(_normalize_name)
    candidate_names = candidate_names.dropna(subset=["mlbam_id"])
    candidate_names = candidate_names[candidate_names["name_key"] != ""].drop_duplicates()

    merged = provider.merge(candidate_names, on="name_key", how="left")
    match_counts = merged.groupby("external_player_id")["mlbam_id"].nunique(dropna=True).rename("match_count")
    merged = merged.merge(match_counts, on="external_player_id", how="left")
    out = merged[merged["match_count"].eq(1)].copy()
    out = out[["external_player_id", "mlbam_id", "player_name", "matched_name"]].drop_duplicates("external_player_id")
    out = out.rename(columns={"mlbam_id": "player_id"})
    return out.sort_values("external_player_id").reset_index(drop=True)


def build_external_game_id_map(provider_lineups: pd.DataFrame, mlb_games: pd.DataFrame) -> pd.DataFrame:
    """Map provider game IDs to MLBAM game IDs by date and team matchup."""

    required_provider = {"external_game_id", "game_date", "home_team", "away_team"}
    missing_provider = required_provider - set(provider_lineups.columns)
    if missing_provider:
        raise ValueError(f"provider_lineups is missing columns: {sorted(missing_provider)}")
    required_games = {"game_id", "game_date", "home_team", "away_team"}
    missing_games = required_games - set(mlb_games.columns)
    if missing_games:
        raise ValueError(f"mlb_games is missing columns: {sorted(missing_games)}")

    provider = provider_lineups[list(required_provider)].dropna().drop_duplicates().copy()
    provider["date_key"] = _date_key(provider["game_date"])
    provider["home_key"] = provider["home_team"].astype(str).str.upper()
    provider["away_key"] = provider["away_team"].astype(str).str.upper()

    games = mlb_games[list(required_games)].dropna().drop_duplicates().copy()
    games["date_key"] = _date_key(games["game_date"])
    games["home_key"] = games["home_team"].astype(str).str.upper()
    games["away_key"] = games["away_team"].astype(str).str.upper()

    merged = provider.merge(
        games[["game_id", "date_key", "home_key", "away_key"]],
        on=["date_key", "home_key", "away_key"],
        how="left",
    )
    match_counts = merged.groupby("external_game_id")["game_id"].nunique(dropna=True).rename("match_count")
    merged = merged.merge(match_counts, on="external_game_id", how="left")
    out = merged[merged["match_count"].eq(1)].copy()
    out = out[["external_game_id", "game_id", "game_date", "home_team", "away_team"]].drop_duplicates("external_game_id")
    return out.sort_values("external_game_id").reset_index(drop=True)


def read_mlb_people_tables(paths: list[str | Path]) -> pd.DataFrame:
    frames = [read_csv_table(path) for path in paths if Path(path).exists()]
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates()


def write_id_map(
    *,
    chadwick_people_csv: str | Path,
    output: str | Path,
    mlb_people_csvs: list[str | Path] | None = None,
) -> Path:
    chadwick = read_csv_table(chadwick_people_csv)
    mlb_people = read_mlb_people_tables(mlb_people_csvs or [])
    id_map = build_id_map(chadwick, mlb_people)
    write_csv_table(id_map, output)
    return Path(output)
