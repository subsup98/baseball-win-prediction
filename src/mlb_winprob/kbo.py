"""KBO source-specific normalization helpers."""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd

KBO_TEAM_NAMES = [
    "Doosan Bears",
    "Hanwha Eagles",
    "Kia Tigers",
    "Kiwoom Heroes",
    "KT Wiz",
    "LG Twins",
    "Lotte Giants",
    "NC Dinos",
    "Samsung Lions",
    "SSG Landers",
]

KBO_TEAM_ABBREVIATIONS = {
    "Doosan": "Doosan Bears",
    "Hanwha": "Hanwha Eagles",
    "Kia": "Kia Tigers",
    "Kiwoom": "Kiwoom Heroes",
    "KT": "KT Wiz",
    "LG": "LG Twins",
    "Lotte": "Lotte Giants",
    "NC": "NC Dinos",
    "Samsung": "Samsung Lions",
    "SSG": "SSG Landers",
}


def _clean_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return " ".join(value.replace("\xa0", " ").replace("혻", " ").split())


def _split_rank_player(value: object) -> tuple[float, str | None]:
    text = str(_clean_text(value) or "")
    match = re.match(r"^\s*(\d+)\s+(.+?)\s*$", text)
    if not match:
        return np.nan, text or None
    return float(match.group(1)), match.group(2)


def _extract_player_id_from_href(value: object) -> float:
    if not isinstance(value, str):
        return np.nan
    match = re.search(r"/players/(\d+)-", value)
    return float(match.group(1)) if match else np.nan


def _player_link_lookup(links_csv: Path) -> pd.DataFrame:
    if not links_csv.exists():
        return pd.DataFrame(columns=["player_name", "mykbo_player_id", "player_href"])
    links = pd.read_csv(links_csv)
    if not {"text", "href"}.issubset(links.columns):
        return pd.DataFrame(columns=["player_name", "mykbo_player_id", "player_href"])
    links = links[links["href"].astype(str).str.contains(r"/players/\d+-", regex=True, na=False)].copy()
    links["player_name"] = links["text"].map(_clean_text)
    links["mykbo_player_id"] = links["href"].map(_extract_player_id_from_href)
    links = links[links["player_name"].astype(str).str.len() > 0]
    return (
        links.rename(columns={"href": "player_href"})[["player_name", "mykbo_player_id", "player_href"]]
        .drop_duplicates(["player_name", "mykbo_player_id"])
        .reset_index(drop=True)
    )


def _numeric(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column in out.columns:
            out[column] = pd.to_numeric(out[column].map(_clean_text), errors="coerce")
    return out


def _parse_ip(value: object) -> float:
    text = str(_clean_text(value) or "")
    if not text or text.lower() == "nan":
        return np.nan
    thirds = 0.0
    if "&frac13;" in text or "1/3" in text:
        thirds = 1 / 3
    elif "&frac23;" in text or "2/3" in text:
        thirds = 2 / 3
    whole = re.sub(r"&frac(?:13|23);|[12]/3", "", text).strip()
    number = pd.to_numeric(whole, errors="coerce")
    if pd.isna(number):
        return np.nan
    return float(number) + thirds


def _parse_boxscore_player(value: object) -> tuple[float, str | None]:
    text = str(_clean_text(value) or "")
    text = re.sub(r"^[?]+", "", text).strip()
    match = re.match(r"^(?:(\d+)\s+)?(.+?)(?:\s+#\d+)?$", text)
    if not match:
        return np.nan, text or None
    order = float(match.group(1)) if match.group(1) else np.nan
    return order, match.group(2).strip()


def _standardize_ranked_players(
    table_csv: Path,
    links_csv: Path,
    *,
    season: int,
    role: str,
) -> pd.DataFrame:
    frame = pd.read_csv(table_csv)
    if "Rank / Player" in frame.columns:
        split = frame["Rank / Player"].map(_split_rank_player)
        frame["rank"] = [item[0] for item in split]
        frame["player_name"] = [item[1] for item in split]
        frame = frame.drop(columns=["Rank / Player"])
    frame.insert(0, "season", season)
    frame.insert(1, "role", role)
    frame = frame.rename(columns={"Team": "team", "HB": "hit_by_pitch"})
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = frame[column].map(_clean_text)
    if "IP" in frame.columns:
        frame["IP"] = frame["IP"].map(_parse_ip)
    numeric_columns = [column for column in frame.columns if column not in {"role", "player_name", "team"}]
    frame = _numeric(frame, numeric_columns)
    lookup = _player_link_lookup(links_csv)
    if not lookup.empty and "player_name" in frame.columns:
        frame = frame.merge(lookup, on="player_name", how="left")
    return frame


def _standardize_team_split(table_csv: Path, *, season: int, split_name: str) -> pd.DataFrame:
    frame = pd.read_csv(table_csv)
    if frame.empty:
        return frame
    first_column = frame.columns[0]
    frame = frame.rename(columns={first_column: "team"})
    frame.insert(0, "season", season)
    frame.insert(1, "split", split_name)
    for column in frame.select_dtypes(include=["object", "string"]).columns:
        frame[column] = frame[column].map(_clean_text)
    numeric_columns = [column for column in frame.columns if column not in {"team", "split"}]
    return _numeric(frame, numeric_columns)


def _standardize_league_summary(table_csv: Path, *, season: int) -> pd.DataFrame:
    frame = pd.read_csv(table_csv)
    if frame.empty or frame.shape[1] < 2:
        return pd.DataFrame(columns=["season", "metric", "value"])
    out = frame.iloc[:, :2].copy()
    out.columns = ["metric", "value"]
    out.insert(0, "season", season)
    out["metric"] = out["metric"].map(_clean_text)
    out["value"] = out["value"].map(_clean_text)
    return out


def standardize_mykbo_tables(input_dir: str | Path, output_dir: str | Path, *, season: int) -> dict[str, Path]:
    """Create named KBO secondary-source tables from parsed MyKBO HTML tables."""

    source = Path(input_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs: dict[str, Path] = {}

    table_specs = [
        ("batting_season", "batting_ops", "hitter"),
        ("pitching_season", "pitching_era", "pitcher"),
    ]
    for output_name, prefix, role in table_specs:
        table = source / f"{prefix}_{season}_table_1.csv"
        links = source / f"{prefix}_{season}_links.csv"
        if table.exists():
            frame = _standardize_ranked_players(table, links, season=season, role=role)
            path = target / f"{output_name}.csv"
            frame.to_csv(path, index=False)
            outputs[output_name] = path

    league_summary = source / f"stats_{season}_table_1.csv"
    if league_summary.exists():
        frame = _standardize_league_summary(league_summary, season=season)
        path = target / "league_summary.csv"
        frame.to_csv(path, index=False)
        outputs["league_summary"] = path

    team_frames = []
    for path in sorted(source.glob(f"team_splits_{season}_table_*.csv")):
        match = re.search(r"_table_(\d+)\.csv$", path.name)
        if not match:
            continue
        index = int(match.group(1))
        split_name = "season" if index == 1 else f"split_{index}"
        if index == 2:
            split_name = "home"
        elif index == 3:
            split_name = "away"
        team_frames.append(_standardize_team_split(path, season=season, split_name=split_name))
    if team_frames:
        frame = pd.concat(team_frames, ignore_index=True)
        path = target / "team_splits.csv"
        frame.to_csv(path, index=False)
        outputs["team_splits"] = path

    for prefix, output_name in [
        ("foreign_players", "foreign_players_raw"),
        ("park_splits", "park_splits_raw"),
    ]:
        frames = []
        for path in sorted(source.glob(f"{prefix}_{season}_table_*.csv")):
            frame = pd.read_csv(path)
            frame.insert(0, "season", season)
            frame.insert(1, "source_table", path.stem)
            for column in frame.select_dtypes(include=["object", "string"]).columns:
                frame[column] = frame[column].map(_clean_text)
            frames.append(frame)
        if frames:
            frame = pd.concat(frames, ignore_index=True)
            path = target / f"{output_name}.csv"
            frame.to_csv(path, index=False)
            outputs[output_name] = path

    return outputs


def _game_id_from_href(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"/games/(\d+)-", value)
    return match.group(1) if match else None


def _game_date_from_href(value: object) -> pd.Timestamp | pd.NaT:
    if not isinstance(value, str):
        return pd.NaT
    match = re.search(r"-(\d{8})(?:$|[/?#])", value)
    if not match:
        return pd.NaT
    return pd.to_datetime(match.group(1), format="%Y%m%d", errors="coerce")


def _parse_mykbo_game_text(text: object) -> dict[str, object]:
    clean = str(_clean_text(text) or "")
    team_pattern = "|".join(re.escape(team) for team in sorted(KBO_TEAM_NAMES, key=len, reverse=True))
    final_pattern = re.compile(
        rf"^(?P<away>{team_pattern}) (?P<away_score>\d+) : (?P<home_score>\d+) "
        rf"(?P<status>Final(?:/\d+)?) (?P<home>{team_pattern})$"
    )
    live_pattern = re.compile(
        rf"^(?P<away>{team_pattern}) (?P<away_score>\d+) : (?P<home_score>\d+) "
        rf"(?P<status>(?:Top|Bot) \d+(?:st|nd|rd|th)) (?P<home>{team_pattern})$"
    )
    canceled_pattern = re.compile(
        rf"^(?P<away>{team_pattern}) Canceled(?: (?P<reason>.+?))? (?P<home>{team_pattern})$"
    )
    scheduled_pattern = re.compile(
        rf"^(?P<away>{team_pattern}) (?P<scheduled_time>\d{{1,2}}:\d{{2}}(?:am|pm)) "
        rf"(?P<venue>.+?) (?P<home>{team_pattern})$",
        flags=re.IGNORECASE,
    )
    match = final_pattern.match(clean)
    if match:
        data = match.groupdict()
        return {
            "away_team": data["away"],
            "home_team": data["home"],
            "away_score": int(data["away_score"]),
            "home_score": int(data["home_score"]),
            "status": data["status"],
            "is_final": 1,
            "is_live": 0,
            "is_canceled": 0,
            "cancel_reason": None,
            "scheduled_time": None,
            "venue_name": None,
        }
    match = live_pattern.match(clean)
    if match:
        data = match.groupdict()
        return {
            "away_team": data["away"],
            "home_team": data["home"],
            "away_score": int(data["away_score"]),
            "home_score": int(data["home_score"]),
            "status": data["status"],
            "is_final": 0,
            "is_live": 1,
            "is_canceled": 0,
            "cancel_reason": None,
            "scheduled_time": None,
            "venue_name": None,
        }
    match = canceled_pattern.match(clean)
    if match:
        data = match.groupdict()
        return {
            "away_team": data["away"],
            "home_team": data["home"],
            "away_score": np.nan,
            "home_score": np.nan,
            "status": "Canceled",
            "is_final": 0,
            "is_live": 0,
            "is_canceled": 1,
            "cancel_reason": data.get("reason"),
            "scheduled_time": None,
            "venue_name": None,
        }
    match = scheduled_pattern.match(clean)
    if match:
        data = match.groupdict()
        return {
            "away_team": data["away"],
            "home_team": data["home"],
            "away_score": np.nan,
            "home_score": np.nan,
            "status": "Scheduled",
            "is_final": 0,
            "is_live": 0,
            "is_canceled": 0,
            "cancel_reason": None,
            "scheduled_time": data["scheduled_time"].lower(),
            "venue_name": data["venue"],
        }
    return {
        "away_team": None,
        "home_team": None,
        "away_score": np.nan,
        "home_score": np.nan,
        "status": None,
        "is_final": 0,
        "is_live": 0,
        "is_canceled": 0,
        "cancel_reason": None,
        "scheduled_time": None,
        "venue_name": None,
    }


def standardize_mykbo_schedule_links(input_dir: str | Path, output: str | Path) -> Path:
    """Create a KBO games.csv draft from parsed MyKBO schedule link files."""

    source = Path(input_dir)
    rows: list[dict[str, object]] = []
    for path in sorted(source.glob("schedule_week_of_*_links.csv")):
        links = pd.read_csv(path)
        if not {"text", "href"}.issubset(links.columns):
            continue
        games = links[links["href"].astype(str).str.contains(r"^/games/\d+-", regex=True, na=False)].copy()
        for _, row in games.iterrows():
            parsed = _parse_mykbo_game_text(row["text"])
            rows.append(
                {
                    "game_id": _game_id_from_href(row["href"]),
                    "game_date": _game_date_from_href(row["href"]),
                    "season": _game_date_from_href(row["href"]).year
                    if pd.notna(_game_date_from_href(row["href"]))
                    else np.nan,
                    "source_text": _clean_text(row["text"]),
                    "source_href": row["href"],
                    **parsed,
                }
            )
    frame = pd.DataFrame(rows)
    if not frame.empty:
        frame = frame.drop_duplicates("game_id", keep="last")
        frame["game_date"] = pd.to_datetime(frame["game_date"], errors="coerce")
        frame["home_team_win"] = np.where(
            frame["home_score"].notna() & frame["away_score"].notna(),
            (pd.to_numeric(frame["home_score"], errors="coerce") > pd.to_numeric(frame["away_score"], errors="coerce")).astype(int),
            np.nan,
        )
        frame = frame.sort_values(["game_date", "game_id"]).reset_index(drop=True)
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(target, index=False)
    return target


def _game_page_link_lookup(links_csv: Path) -> pd.DataFrame:
    lookup = _player_link_lookup(links_csv)
    if lookup.empty:
        return lookup
    return lookup.drop_duplicates("player_name", keep="first")


def _standardize_game_batting_table(path: Path, links_csv: Path, games: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    game_id = path.name.split("_", 1)[0]
    team_abbrev = frame.columns[0]
    team = KBO_TEAM_ABBREVIATIONS.get(team_abbrev, team_abbrev)
    split = frame[team_abbrev].map(_parse_boxscore_player)
    frame["batting_order"] = [item[0] for item in split]
    frame["player_name"] = [item[1] for item in split]
    frame = frame.drop(columns=[team_abbrev])
    frame = frame.rename(
        columns={
            "Pos": "position",
            "BA": "batting_average_after_game",
            "AB": "at_bats",
            "R": "runs",
            "H": "hits",
            "HR": "home_runs",
            "RBI": "rbi",
            "BB": "walks",
            "SO": "strikeouts",
            "HBP": "hit_by_pitch",
        }
    )
    frame.insert(0, "game_id", game_id)
    frame.insert(1, "team", team)
    lookup = _game_page_link_lookup(links_csv)
    if not lookup.empty:
        frame = frame.merge(lookup, on="player_name", how="left")
    frame = frame.merge(games[["game_id", "game_date", "season"]], on="game_id", how="left")
    numeric_columns = [
        "batting_order",
        "batting_average_after_game",
        "at_bats",
        "runs",
        "hits",
        "home_runs",
        "rbi",
        "walks",
        "strikeouts",
        "hit_by_pitch",
    ]
    frame = _numeric(frame, numeric_columns)
    frame["doubles"] = np.nan
    frame["triples"] = np.nan
    frame["sacrifice_flies"] = np.nan
    frame["total_bases"] = np.nan
    frame["plate_appearances"] = (
        frame["at_bats"].fillna(0) + frame["walks"].fillna(0) + frame["hit_by_pitch"].fillna(0)
    )
    return frame


def _standardize_game_pitching_table(path: Path, links_csv: Path, games: pd.DataFrame) -> pd.DataFrame:
    frame = pd.read_csv(path)
    if frame.empty:
        return frame
    game_id = path.name.split("_", 1)[0]
    team_abbrev = frame.columns[0]
    team = KBO_TEAM_ABBREVIATIONS.get(team_abbrev, team_abbrev)
    split = frame[team_abbrev].map(_parse_boxscore_player)
    frame["player_name"] = [item[1] for item in split]
    frame = frame.drop(columns=[team_abbrev])
    frame = frame.rename(
        columns={
            "ERA": "era_after_game",
            "IP": "innings_pitched",
            "NP": "pitches",
            "R": "runs",
            "ER": "earned_runs",
            "H": "hits",
            "HR": "home_runs",
            "SO": "strikeouts",
            "BB": "walks",
            "HB": "hit_by_pitch",
            "GS": "game_score",
        }
    )
    frame.insert(0, "game_id", game_id)
    frame.insert(1, "team", team)
    lookup = _game_page_link_lookup(links_csv)
    if not lookup.empty:
        frame = frame.merge(lookup, on="player_name", how="left")
    frame = frame.merge(games[["game_id", "game_date", "season"]], on="game_id", how="left")
    if "innings_pitched" in frame.columns:
        frame["innings_pitched"] = frame["innings_pitched"].map(_parse_ip)
    numeric_columns = [
        "era_after_game",
        "innings_pitched",
        "pitches",
        "runs",
        "earned_runs",
        "hits",
        "home_runs",
        "strikeouts",
        "walks",
        "hit_by_pitch",
        "game_score",
    ]
    frame = _numeric(frame, numeric_columns)
    frame["batters_faced"] = np.nan
    frame["is_start"] = frame.groupby("game_id").cumcount().eq(0).astype(int)
    return frame


def _classify_game_table(path: Path) -> str | None:
    """Identify a parsed MyKBO game table as batting, pitching, or other by columns."""

    try:
        header = pd.read_csv(path, nrows=0)
    except Exception:
        return None
    columns = {str(c) for c in header.columns}
    # Batting boxscore tables expose Pos/AB/BA; pitching tables expose ERA/IP/NP.
    if "ERA" in columns and "IP" in columns:
        return "pitching"
    if "Pos" in columns and "AB" in columns:
        return "batting"
    return None


def standardize_mykbo_game_tables(input_dir: str | Path, games_csv: str | Path, output_dir: str | Path) -> dict[str, Path]:
    """Create canonical-ish game logs from parsed MyKBO game page tables."""

    source = Path(input_dir)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    games = pd.read_csv(games_csv, dtype={"game_id": str})
    games["game_id"] = games["game_id"].astype(str)
    batting_frames = []
    pitching_frames = []
    for links_csv in sorted(source.glob("*_game_links.csv")):
        game_id = links_csv.name.split("_", 1)[0]
        table_paths = sorted(source.glob(f"{game_id}_game_table_*.csv"))
        for table_path in table_paths:
            # Classify each boxscore table by its columns rather than position.
            # Game pages vary in table count across seasons (some carry an extra
            # header table), so a positional 1,2/3,4 rule misaligns older seasons.
            kind = _classify_game_table(table_path)
            if kind == "batting":
                batting_frames.append(_standardize_game_batting_table(table_path, links_csv, games))
            elif kind == "pitching":
                pitching_frames.append(_standardize_game_pitching_table(table_path, links_csv, games))

    outputs: dict[str, Path] = {}
    if batting_frames:
        batting = pd.concat(batting_frames, ignore_index=True)
        path = target / "batting_logs.csv"
        batting.to_csv(path, index=False)
        outputs["batting_logs"] = path
        lineups = batting[batting["batting_order"].notna()].copy()
        lineups = lineups[
            [
                "game_id",
                "team",
                "mykbo_player_id",
                "player_name",
                "batting_order",
                "position",
                "game_date",
                "season",
            ]
        ].rename(columns={"mykbo_player_id": "player_id"})
        lineups["prediction_mode"] = "confirmed_lineup"
        lineups["lineup_source"] = "mykbo_game_page"
        lineups["lineup_confidence"] = 1.0
        path = target / "lineups.csv"
        lineups.to_csv(path, index=False)
        outputs["lineups"] = path
    if pitching_frames:
        pitching = pd.concat(pitching_frames, ignore_index=True)
        path = target / "pitcher_logs.csv"
        pitching.to_csv(path, index=False)
        outputs["pitcher_logs"] = path
    return outputs
