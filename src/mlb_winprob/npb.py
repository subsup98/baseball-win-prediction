"""NPB source-specific normalization helpers."""

from __future__ import annotations

from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import pandas as pd

from mlb_winprob.constants import NON_FEATURE_COLUMNS


def _clean_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return " ".join(value.replace("\xa0", " ").split())


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(
                out[column].map(lambda value: str(value).replace(",", "") if pd.notna(value) else value),
                errors="coerce",
            )
    return out


def _read_first_existing(source: Path, stems: list[str]) -> pd.DataFrame | None:
    for stem in stems:
        path = source / f"{stem}_table_1.csv"
        if path.exists():
            return pd.read_csv(path)
    return None


def _read_optional_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path, dtype={"game_id": str, "player_id": str})


def _venue_id(value: object) -> str:
    text = str(_clean_text(value) or "").lower()
    keep = [character if character.isalnum() else "_" for character in text]
    return "npb_" + "_".join("".join(keep).split("_")).strip("_")


def _pct(part: int | float, whole: int | float) -> float:
    if not whole:
        return 0.0
    return round(float(part) / float(whole) * 100.0, 1)


def _missing_text_count(series: pd.Series) -> int:
    text = series.astype("string").str.strip()
    blank = text[text.notna()].isin(["", "nan", "<NA>"]).sum()
    return int(text.isna().sum() + blank)


def _parse_baseball_ip(value: object) -> float:
    if pd.isna(value):
        return 0.0
    text = str(value).strip().replace("+", "")
    if not text:
        return 0.0
    if "." not in text:
        return float(text)
    whole, fraction = text.split(".", 1)
    outs = int(fraction[:1] or 0)
    return float(int(whole or 0) + outs / 3)


def _proeyekyuu_player_lookup(links_csv: Path) -> pd.DataFrame:
    if not links_csv.exists():
        return pd.DataFrame(columns=["player_name", "player_id", "player_href"])
    links = pd.read_csv(links_csv)
    if not {"text", "href"}.issubset(links.columns):
        return pd.DataFrame(columns=["player_name", "player_id", "player_href"])
    out = links[links["href"].astype(str).str.contains(r"PlayerID=", na=False)].copy()
    out["player_name"] = out["text"].map(_clean_text)
    out["player_id"] = out["href"].astype(str).str.extract(r"PlayerID=([^&#]+)", expand=False)
    out = out[out["player_name"].astype(str).str.len() > 0]
    return out.rename(columns={"href": "player_href"})[["player_name", "player_id", "player_href"]].drop_duplicates("player_name")


def _standardize_proeyekyuu_player_table(frame: pd.DataFrame, *, season: int, role: str) -> pd.DataFrame:
    out = frame.copy()
    for column in out.select_dtypes(include=["object", "string"]).columns:
        out[column] = out[column].map(_clean_text)
    if "Season" in out.columns:
        out = out[out["Season"].astype(str).eq(str(season))].copy()
    out.insert(0, "source", "proeyekyuu")
    out.insert(1, "role", role)
    out = out.rename(
        columns={
            "Season": "season",
            "Name": "player_name",
            "PlayerID": "player_id",
            "Team": "team",
            "Game Type": "game_type",
            "Position": "position",
            "PA": "plate_appearances",
            "AB": "at_bats",
            "R": "runs",
            "H": "hits",
            "2B": "doubles",
            "3B": "triples",
            "HR": "home_runs",
            "RBI": "rbi",
            "BB": "walks",
            "IBB": "intentional_walks",
            "K": "strikeouts",
            "SO": "strikeouts",
            "HBP": "hit_by_pitch",
            "HP": "hit_by_pitch",
            "SF": "sacrifice_flies",
            "SH": "sacrifice_hits",
            "TB": "total_bases",
            "IP": "innings_pitched",
            "ER": "earned_runs",
            "ERA": "era",
            "WHIP": "whip",
        }
    )
    numeric_columns = [
        column
        for column in out.columns
        if column
        not in {
            "source",
            "role",
            "player_name",
            "team",
            "game_type",
            "position",
            "League",
            "League (Short)",
            "Last Name",
            "Position (Long)",
        }
    ]
    return _numeric(out, numeric_columns).reset_index(drop=True)


def _standardize_proeyekyuu_team_table(frame: pd.DataFrame, *, season: int, role: str) -> pd.DataFrame:
    out = frame.copy()
    for column in out.select_dtypes(include=["object", "string"]).columns:
        out[column] = out[column].map(_clean_text)
    if "Season" in out.columns:
        out = out[out["Season"].astype(str).eq(str(season))].copy()
    out.insert(0, "source", "proeyekyuu")
    out.insert(1, "role", role)
    out = out.rename(
        columns={
            "Season": "season",
            "Team": "team",
            "Game Type": "game_type",
            "PA": "plate_appearances",
            "AB": "at_bats",
            "R": "runs",
            "H": "hits",
            "2B": "doubles",
            "3B": "triples",
            "HR": "home_runs",
            "RBI": "rbi",
            "BB": "walks",
            "IBB": "intentional_walks",
            "K": "strikeouts",
            "SO": "strikeouts",
            "HBP": "hit_by_pitch",
            "HP": "hit_by_pitch",
            "SF": "sacrifice_flies",
            "SH": "sacrifice_hits",
            "TB": "total_bases",
            "IP": "innings_pitched",
            "ER": "earned_runs",
            "ERA": "era",
            "WHIP": "whip",
        }
    )
    numeric_columns = [
        column
        for column in out.columns
        if column not in {"source", "role", "team", "game_type", "League", "League Logo URL"}
    ]
    return _numeric(out, numeric_columns).reset_index(drop=True)


def standardize_proeyekyuu_tables(input_dir: str | Path, output_dir: str | Path, *, season: int) -> dict[str, Path]:
    """Create named NPB secondary-source tables from parsed ProEyeKyuu pages."""

    source = Path(input_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    player_specs = [
        ("batting_season", ["player_batting_stats", f"player_batting_stats_{season}"], "hitter"),
        ("pitching_season", ["player_pitching_stats", f"player_pitching_stats_{season}"], "pitcher"),
        ("fielding_season", ["player_fielding_stats", f"player_fielding_stats_{season}"], "fielder"),
    ]
    for output_name, stems, role in player_specs:
        frame = _read_first_existing(source, stems)
        if frame is not None:
            out = _standardize_proeyekyuu_player_table(frame, season=season, role=role)
            path = target / f"{output_name}.csv"
            out.to_csv(path, index=False)
            outputs[output_name] = path

    team_specs = [
        ("team_batting_season", ["team_batting_stats", f"team_batting_stats_{season}"], "team_batting"),
        ("team_pitching_season", ["team_pitching_stats", f"team_pitching_stats_{season}"], "team_pitching"),
        ("team_fielding_season", ["team_fielding_stats", f"team_fielding_stats_{season}"], "team_fielding"),
    ]
    for output_name, stems, role in team_specs:
        frame = _read_first_existing(source, stems)
        if frame is not None:
            out = _standardize_proeyekyuu_team_table(frame, season=season, role=role)
            path = target / f"{output_name}.csv"
            out.to_csv(path, index=False)
            outputs[output_name] = path

    registry = _read_first_existing(source, ["player_registry", f"player_registry_{season}"])
    if registry is not None:
        out = registry.copy()
        for column in out.select_dtypes(include=["object", "string"]).columns:
            out[column] = out[column].map(_clean_text)
        out = out.rename(columns={"Name": "player_name", "PlayerID": "player_id"})
        path = target / "player_registry.csv"
        out.to_csv(path, index=False)
        outputs["player_registry"] = path

    return outputs


def standardize_proeyekyuu_game_results(input_dir: str | Path, output: str | Path) -> Path:
    """Create a project-standard NPB games table from ProEyeKyuu game results."""

    source = Path(input_dir)
    table = source / "game_results_table_1.csv"
    if not table.exists():
        raise FileNotFoundError(f"Missing ProEyeKyuu game results table: {table}")
    frame = pd.read_csv(table)
    required = {"GameID", "Season", "Date", "Game Type", "Team", "Home or Away", "Score", "Other Team", "Ballpark"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"ProEyeKyuu game results table is missing columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for game_id, group in frame.groupby("GameID", sort=False):
        home = group[group["Home or Away"].astype(str).str.lower().eq("home")]
        away = group[group["Home or Away"].astype(str).str.lower().eq("away")]
        if home.empty or away.empty:
            continue
        home_row = home.iloc[0]
        away_row = away.iloc[0]
        rows.append(
            {
                "game_id": game_id,
                "game_date": home_row["Date"],
                "season": home_row["Season"],
                "game_type": home_row["Game Type"],
                "home_team": home_row["Team"],
                "away_team": away_row["Team"],
                "home_sp_id": pd.NA,
                "away_sp_id": pd.NA,
                "home_score": home_row["Score"],
                "away_score": away_row["Score"],
                "venue_id": pd.NA,
                "venue_name": home_row["Ballpark"],
                "source_href": f"https://proeyekyuu.com/game/?GameID={game_id}",
                "source": "proeyekyuu_game_results",
            }
        )
    out = pd.DataFrame(rows)
    if not out.empty:
        out["game_date"] = pd.to_datetime(out["game_date"], errors="coerce")
        for column in ["season", "home_score", "away_score"]:
            out[column] = pd.to_numeric(out[column], errors="coerce")
        out = out.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)
    return target


def _classify_proeyekyuu_game_table(path: Path) -> str | None:
    try:
        columns = {str(column) for column in pd.read_csv(path, nrows=0).columns}
    except Exception:
        return None
    if "Pitcher" in columns and {"IP", "BF"}.issubset(columns):
        return "pitching"
    if "Batter" in columns and {"AB", "R", "H"}.issubset(columns):
        return "batting"
    return None


def _standardize_proeyekyuu_game(links_csv_raw: str, game: dict[str, object]) -> tuple[list[pd.DataFrame], list[pd.DataFrame]]:
    links_csv = Path(links_csv_raw)
    source = links_csv.parent
    game_id = links_csv.name.split("_game_links.csv", 1)[0]
    team_by_side = {"away": game.get("away_team"), "home": game.get("home_team")}
    lookup = _proeyekyuu_player_lookup(links_csv)
    table_paths = sorted(source.glob(f"{game_id}_game_table_*.csv"), key=lambda path: int(path.stem.rsplit("_", 1)[-1]))
    typed_paths: dict[str, list[Path]] = {"pitching": [], "batting": []}
    seen_signatures: set[tuple[str, tuple[str, ...]]] = set()
    for table_path in table_paths:
        kind = _classify_proeyekyuu_game_table(table_path)
        if kind is None:
            continue
        frame = pd.read_csv(table_path)
        player_column = "Pitcher" if kind == "pitching" else "Batter"
        signature = (kind, tuple(frame[player_column].astype(str).tolist()))
        if signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        typed_paths[kind].append(table_path)

    batting_frames = []
    pitching_frames = []
    for side, table_path in zip(["away", "home"], typed_paths["batting"]):
        frame = pd.read_csv(table_path)
        if "GameID" not in frame.columns:
            frame["GameID"] = game_id
        out = frame.rename(
            columns={
                "GameID": "game_id",
                "Batter": "player_name",
                "Order": "batting_order",
                "Pos": "position",
                "AB": "at_bats",
                "R": "runs",
                "H": "hits",
                "RBI": "rbi",
                "SB": "stolen_bases",
            }
        )
        out.insert(1, "team", team_by_side[side])
        out["game_date"] = game.get("game_date")
        out["season"] = game.get("season")
        if not lookup.empty:
            out = out.merge(lookup, on="player_name", how="left")
        for column in ["batting_order", "at_bats", "runs", "hits", "rbi", "stolen_bases"]:
            out[column] = pd.to_numeric(out.get(column), errors="coerce")
        out["doubles"] = 0.0
        out["triples"] = 0.0
        out["home_runs"] = 0.0
        out["walks"] = 0.0
        out["hit_by_pitch"] = 0.0
        out["sacrifice_flies"] = 0.0
        out["total_bases"] = out["hits"].fillna(0.0)
        out["plate_appearances"] = out["at_bats"].fillna(0.0)
        out["opposing_pitcher_hand"] = pd.NA
        batting_frames.append(out)

    for side, table_path in zip(["away", "home"], typed_paths["pitching"]):
        frame = pd.read_csv(table_path)
        if "GameID" not in frame.columns:
            frame["GameID"] = game_id
        out = frame.rename(
            columns={
                "GameID": "game_id",
                "Pitcher": "player_name",
                "NP": "pitches",
                "BF": "batters_faced",
                "IP": "innings_pitched",
                "H": "hits",
                "HR": "home_runs",
                "BB": "walks",
                "DB": "hit_by_pitch",
                "K": "strikeouts",
                "R": "runs",
                "ER": "earned_runs",
            }
        )
        out.insert(1, "team", team_by_side[side])
        out["game_date"] = game.get("game_date")
        out["season"] = game.get("season")
        if not lookup.empty:
            out = out.merge(lookup, on="player_name", how="left")
        for column in ["pitches", "batters_faced", "hits", "home_runs", "walks", "hit_by_pitch", "strikeouts", "runs", "earned_runs", "Index"]:
            out[column] = pd.to_numeric(out.get(column), errors="coerce")
        out["innings_pitched"] = out["innings_pitched"].map(_parse_baseball_ip)
        out["is_start"] = out["Index"].fillna(9999).eq(0).astype(int)
        out["role"] = out["is_start"].map(lambda value: "SP" if value == 1 else "RP")
        decision = out.get("column_1", pd.Series(index=out.index, dtype=object)).astype(str).str.upper().str.strip()
        out["is_closer"] = decision.eq("S").astype(int)
        out["is_high_leverage"] = decision.isin(["S", "H"]).astype(int)
        pitching_frames.append(out)

    return batting_frames, pitching_frames


def standardize_proeyekyuu_game_tables(
    input_dir: str | Path,
    games_csv: str | Path,
    output_dir: str | Path,
    *,
    workers: int = 1,
) -> dict[str, Path]:
    """Create canonical-ish NPB game logs from parsed ProEyeKyuu game pages."""

    source = Path(input_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    games = pd.read_csv(games_csv, dtype={"game_id": str})
    games["game_id"] = games["game_id"].astype(str)
    game_lookup = games.drop_duplicates("game_id").set_index("game_id").to_dict("index")
    batting_frames = []
    pitching_frames = []
    links_paths = sorted(source.glob("*_game_links.csv"))

    if workers <= 1:
        for links_csv in links_paths:
            game_id = links_csv.name.split("_game_links.csv", 1)[0]
            batting, pitching = _standardize_proeyekyuu_game(str(links_csv), game_lookup.get(game_id, {}))
            batting_frames.extend(batting)
            pitching_frames.extend(pitching)
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            futures = []
            for links_csv in links_paths:
                game_id = links_csv.name.split("_game_links.csv", 1)[0]
                futures.append(executor.submit(_standardize_proeyekyuu_game, str(links_csv), game_lookup.get(game_id, {})))
            for future in as_completed(futures):
                batting, pitching = future.result()
                batting_frames.extend(batting)
                pitching_frames.extend(pitching)

    outputs: dict[str, Path] = {}
    if batting_frames:
        batting = pd.concat(batting_frames, ignore_index=True)
        batting_columns = [
            "game_id",
            "game_date",
            "season",
            "player_id",
            "player_name",
            "team",
            "opposing_pitcher_hand",
            "at_bats",
            "hits",
            "doubles",
            "triples",
            "home_runs",
            "walks",
            "hit_by_pitch",
            "sacrifice_flies",
            "total_bases",
            "plate_appearances",
        ]
        path = target / "batting_logs.csv"
        batting[batting_columns].to_csv(path, index=False)
        outputs["batting_logs"] = path
        lineups = batting[batting["batting_order"].notna()].copy()
        lineups = lineups[
            ["game_id", "team", "player_id", "player_name", "batting_order", "position", "game_date", "season"]
        ]
        lineups["prediction_mode"] = "confirmed_lineup"
        lineups["lineup_source"] = "proeyekyuu_game_page"
        lineups["lineup_confidence"] = 1.0
        path = target / "lineups.csv"
        lineups.to_csv(path, index=False)
        outputs["lineups"] = path
    if pitching_frames:
        pitching = pd.concat(pitching_frames, ignore_index=True)
        pitching_columns = [
            "game_id",
            "game_date",
            "season",
            "player_id",
            "player_name",
            "team",
            "role",
            "is_start",
            "innings_pitched",
            "hits",
            "home_runs",
            "walks",
            "hit_by_pitch",
            "strikeouts",
            "batters_faced",
            "pitches",
            "is_closer",
            "is_high_leverage",
        ]
        path = target / "pitcher_logs.csv"
        pitching[pitching_columns].to_csv(path, index=False)
        outputs["pitcher_logs"] = path
    return outputs


def write_npb_venue_template(games_csv: str | Path, output: str | Path) -> Path:
    """Write a venue metadata template from NPB games."""

    games = pd.read_csv(games_csv)
    if "venue_name" not in games.columns:
        raise ValueError("games is missing columns: ['venue_name']")
    venues = (
        games[["venue_name"]]
        .dropna()
        .drop_duplicates()
        .sort_values("venue_name")
        .reset_index(drop=True)
    )
    venues["venue_id"] = venues["venue_name"].map(_venue_id)
    venues["latitude"] = pd.NA
    venues["longitude"] = pd.NA
    venues["timezone_offset"] = 9
    venues["is_dome"] = pd.NA
    venues["source"] = "npb_venue_template"
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    venues[["venue_id", "venue_name", "latitude", "longitude", "timezone_offset", "is_dome", "source"]].to_csv(target, index=False)
    return target


def write_npb_games_with_venues(games_csv: str | Path, venues_csv: str | Path, output: str | Path) -> Path:
    """Fill stable NPB venue IDs and optional venue metadata into games."""

    games = pd.read_csv(games_csv, dtype={"game_id": str})
    venues = pd.read_csv(venues_csv)
    if "venue_name" not in games.columns:
        raise ValueError("games is missing columns: ['venue_name']")
    required_venues = {"venue_id", "venue_name"}
    missing_venues = required_venues - set(venues.columns)
    if missing_venues:
        raise ValueError(f"venues is missing columns: {sorted(missing_venues)}")

    venue_columns = ["venue_id", "venue_name"]
    for column in ["latitude", "longitude", "timezone_offset", "is_dome"]:
        if column in venues.columns:
            venue_columns.append(column)
    venue_lookup = venues[venue_columns].drop_duplicates("venue_name", keep="last")
    out = games.drop(columns=[column for column in ["venue_id", "venue_latitude", "venue_longitude", "venue_timezone_offset", "is_dome"] if column in games.columns])
    out = out.merge(venue_lookup, on="venue_name", how="left")
    out["venue_id"] = out["venue_id"].fillna(out["venue_name"].map(_venue_id))
    rename = {
        "latitude": "venue_latitude",
        "longitude": "venue_longitude",
        "timezone_offset": "venue_timezone_offset",
    }
    out = out.rename(columns={key: value for key, value in rename.items() if key in out.columns})
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)
    return target


def write_proeyekyuu_games_with_starters(games_csv: str | Path, pitcher_logs_csv: str | Path, output: str | Path) -> Path:
    """Fill NPB games starter IDs from confirmed ProEyeKyuu pitcher logs."""

    games = pd.read_csv(games_csv, dtype={"game_id": str, "home_sp_id": str, "away_sp_id": str})
    pitching = pd.read_csv(pitcher_logs_csv, dtype={"game_id": str, "player_id": str})
    required_games = {"game_id", "home_team", "away_team"}
    required_pitching = {"game_id", "team", "player_id"}
    missing_games = required_games - set(games.columns)
    missing_pitching = required_pitching - set(pitching.columns)
    if missing_games:
        raise ValueError(f"games is missing columns: {sorted(missing_games)}")
    if missing_pitching:
        raise ValueError(f"pitcher_logs is missing columns: {sorted(missing_pitching)}")

    starts = pitching.copy()
    if "is_start" in starts.columns:
        starts = starts[pd.to_numeric(starts["is_start"], errors="coerce").fillna(0).eq(1)].copy()
    elif "role" in starts.columns:
        starts = starts[starts["role"].astype(str).str.upper().eq("SP")].copy()
    sort_columns = [column for column in ["game_id", "team", "innings_pitched", "pitches"] if column in starts.columns]
    ascending = [True, True] + [False] * max(0, len(sort_columns) - 2)
    starts = starts.sort_values(sort_columns, ascending=ascending).drop_duplicates(["game_id", "team"], keep="first")
    starter_columns = ["game_id", "team", "player_id"]
    if "player_name" in starts.columns:
        starter_columns.append("player_name")
    starts = starts[starter_columns].copy()

    out = games.copy()
    for side in ["home", "away"]:
        team_column = f"{side}_team"
        id_column = f"{side}_sp_id"
        name_column = f"{side}_sp_name"
        side_starters = starts.rename(
            columns={
                "team": team_column,
                "player_id": f"{id_column}_confirmed",
                "player_name": f"{name_column}_confirmed",
            }
        )
        out = out.merge(side_starters, on=["game_id", team_column], how="left")
        if id_column not in out.columns:
            out[id_column] = pd.NA
        out[id_column] = out[id_column].where(out[id_column].notna() & out[id_column].astype(str).str.strip().ne(""), out[f"{id_column}_confirmed"])
        out = out.drop(columns=[f"{id_column}_confirmed"])
        confirmed_name = f"{name_column}_confirmed"
        if confirmed_name in out.columns:
            if name_column not in out.columns:
                out[name_column] = pd.NA
            out[name_column] = out[name_column].where(
                out[name_column].notna() & out[name_column].astype(str).str.strip().ne(""),
                out[confirmed_name],
            )
            out = out.drop(columns=[confirmed_name])

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)
    return target


def write_proeyekyuu_batting_detail_audit(input_dir: str | Path, output: str | Path) -> Path:
    """Record which canonical batting event columns are visible in parsed ProEyeKyuu game tables."""

    source = Path(input_dir)
    required = {
        "2B": "doubles",
        "3B": "triples",
        "HR": "home_runs",
        "BB": "walks",
        "DB": "hit_by_pitch",
        "HBP": "hit_by_pitch",
        "SF": "sacrifice_flies",
    }
    observed: set[str] = set()
    batting_tables = 0
    for path in sorted(source.glob("*_game_table_*.csv")):
        kind = _classify_proeyekyuu_game_table(path)
        if kind != "batting":
            continue
        batting_tables += 1
        observed.update(str(column) for column in pd.read_csv(path, nrows=0).columns)

    rows = [
        "# ProEyeKyuu Batting Detail Audit",
        "",
        f"Parsed batting tables scanned: {batting_tables}",
        "",
        "| Canonical field | Source column candidates | Status |",
        "| --- | --- | --- |",
    ]
    for source_column, canonical in required.items():
        status = "available" if source_column in observed else "missing"
        rows.append(f"| `{canonical}` | `{source_column}` | {status} |")
    rows.extend(
        [
            "",
            "Observed batting columns:",
            "",
            ", ".join(f"`{column}`" for column in sorted(observed)) if observed else "_No batting columns found._",
            "",
        ]
    )
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows), encoding="utf-8")
    return target


def write_npb_feature_set(features_csv: str | Path, output: str | Path) -> Path:
    """Write the NPB numeric feature set, excluding MLB-only Statcast columns."""

    features = pd.read_csv(features_csv)
    rows = []
    for column in features.select_dtypes(include=["number", "bool"]).columns:
        if column in NON_FEATURE_COLUMNS:
            status = "excluded"
            reason = "identifier_or_target"
        elif "statcast" in column or column in {
            "home_sp_whiff_rate_to_date",
            "away_sp_whiff_rate_to_date",
            "sp_whiff_rate_diff",
            "home_sp_avg_fastball_velocity_to_date",
            "away_sp_avg_fastball_velocity_to_date",
            "sp_fastball_velocity_diff",
        }:
            status = "excluded"
            reason = "mlb_only_tracking"
        elif features[column].notna().any():
            status = "included"
            reason = "npb_public_or_proxy"
        else:
            status = "excluded"
            reason = "all_null"
        rows.append(
            {
                "column": column,
                "status": status,
                "reason": reason,
                "non_null": int(features[column].notna().sum()),
                "null_rate": float(features[column].isna().mean()),
            }
        )
    out = pd.DataFrame(rows).sort_values(["status", "reason", "column"]).reset_index(drop=True)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)
    return target


def write_npb_model_ready_features(features_csv: str | Path, feature_set_csv: str | Path, output: str | Path) -> Path:
    """Write KBO-style NPB features: identifiers/target plus usable public/proxy columns."""

    features = pd.read_csv(features_csv)
    feature_set = pd.read_csv(feature_set_csv)
    if not {"column", "status"}.issubset(feature_set.columns):
        raise ValueError("feature_set is missing columns: ['column', 'status']")

    metadata_columns = [
        "game_id",
        "game_date",
        "season",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "home_team_win",
        "home_sp_id",
        "away_sp_id",
        "venue_id",
        "prediction_mode",
    ]
    included = feature_set.loc[feature_set["status"].eq("included"), "column"].astype(str).tolist()
    selected = [column for column in metadata_columns if column in features.columns]
    selected.extend(column for column in included if column in features.columns and column not in selected)
    out = features[selected].copy()
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(target, index=False)
    return target


def write_proeyekyuu_coverage_report(games_csv: str | Path, standardized_dir: str | Path, output: str | Path) -> Path:
    """Write an NPB canonical-data coverage report for ProEyeKyuu-derived files."""

    games_path = Path(games_csv)
    source = Path(standardized_dir)
    games = pd.read_csv(games_path, dtype={"game_id": str}) if games_path.exists() else pd.DataFrame()
    batting = _read_optional_csv(source / "batting_logs.csv")
    pitching = _read_optional_csv(source / "pitcher_logs.csv")
    lineups = _read_optional_csv(source / "lineups.csv")

    game_ids = set(games.get("game_id", pd.Series(dtype=str)).dropna().astype(str))
    batting_games = set(batting.get("game_id", pd.Series(dtype=str)).dropna().astype(str))
    pitching_games = set(pitching.get("game_id", pd.Series(dtype=str)).dropna().astype(str))
    lineup_games = set(lineups.get("game_id", pd.Series(dtype=str)).dropna().astype(str))
    canonical_games = batting_games | pitching_games | lineup_games
    home_sp_filled = len(games) - _missing_text_count(games["home_sp_id"]) if "home_sp_id" in games.columns else 0
    away_sp_filled = len(games) - _missing_text_count(games["away_sp_id"]) if "away_sp_id" in games.columns else 0

    lineup_slots = lineups.groupby("game_id").size() if "game_id" in lineups.columns and not lineups.empty else pd.Series(dtype=int)
    starter_counts = (
        pitching[pd.to_numeric(pitching.get("is_start", pd.Series(dtype=float)), errors="coerce").fillna(0).eq(1)]
        .groupby("game_id")
        .size()
        if "game_id" in pitching.columns and not pitching.empty
        else pd.Series(dtype=int)
    )

    player_id_total = int(
        sum(
            frame["player_id"].size
            for frame in [batting, pitching, lineups]
            if "player_id" in frame.columns and not frame.empty
        )
    )
    player_id_missing = int(
        sum(
            _missing_text_count(frame["player_id"])
            for frame in [batting, pitching, lineups]
            if "player_id" in frame.columns and not frame.empty
        )
    )

    batting_proxy_columns = ["doubles", "triples", "home_runs", "walks", "hit_by_pitch", "sacrifice_flies"]
    batting_proxy_note = []
    for column in batting_proxy_columns:
        if column in batting.columns and not batting.empty:
            zero_rate = _pct(int(pd.to_numeric(batting[column], errors="coerce").fillna(0).eq(0).sum()), len(batting))
            batting_proxy_note.append(f"| `{column}` | {zero_rate}% zero/blank |")

    rows = [
        "# NPB ProEyeKyuu Coverage Report",
        "",
        "## Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Scheduled games | {len(games)} |",
        f"| Canonical game coverage | {len(canonical_games)} ({_pct(len(canonical_games), len(game_ids))}%) |",
        f"| Batting log games | {len(batting_games)} ({_pct(len(batting_games), len(game_ids))}%) |",
        f"| Pitching log games | {len(pitching_games)} ({_pct(len(pitching_games), len(game_ids))}%) |",
        f"| Lineup games | {len(lineup_games)} ({_pct(len(lineup_games), len(game_ids))}%) |",
        f"| Batting rows | {len(batting)} |",
        f"| Pitching rows | {len(pitching)} |",
        f"| Lineup rows | {len(lineups)} |",
        f"| Games with home starter ID | {home_sp_filled} ({_pct(home_sp_filled, len(game_ids))}%) |",
        f"| Games with away starter ID | {away_sp_filled} ({_pct(away_sp_filled, len(game_ids))}%) |",
        f"| Player ID missing rate | {_pct(player_id_missing, player_id_total)}% |",
        "",
        "## Game Shape",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Average lineup rows per covered game | {round(float(lineup_slots.mean()), 2) if not lineup_slots.empty else 0.0} |",
        f"| Games with at least 18 lineup rows | {int(lineup_slots.ge(18).sum())} |",
        f"| Games with 2 starters | {int(starter_counts.eq(2).sum())} |",
        "",
        "## MLB Feature Parity Notes",
        "",
        "- The canonical files can feed the existing MLB-style feature builder when game pages are collected.",
        "- Statcast and pitch-level features remain unavailable from the approved NPB source set.",
        "- Public-data proxy features are available for lineup quality, contact power, starter whiff, run prevention, and command.",
        "- ProEyeKyuu game-page pitching tables are close to the canonical MLB inputs; batting tables currently lack event detail for 2B/3B/HR/BB/HBP/SF in the parsed page table.",
        "- Table side assignment assumes the first distinct batting/pitching table is away and the second is home.",
    ]
    if batting_proxy_note:
        rows.extend(["", "## Batting Event Detail Check", "", "| Column | Completeness signal |", "| --- | ---: |"])
        rows.extend(batting_proxy_note)

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(rows) + "\n", encoding="utf-8")
    return target
