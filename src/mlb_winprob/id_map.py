"""Build player ID crosswalks from Chadwick Register and local metadata."""

from __future__ import annotations

from pathlib import Path

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
