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

KBO_PRIMARY_VENUES = {
    "Doosan Bears": "seoul_jamsil",
    "LG Twins": "seoul_jamsil",
    "Kiwoom Heroes": "seoul_gocheok",
    "SSG Landers": "incheon_munhak",
    "KT Wiz": "suwon",
    "Hanwha Eagles": "daejeon",
    "Samsung Lions": "daegu",
    "Kia Tigers": "gwangju",
    "Lotte Giants": "busan_sajik",
    "NC Dinos": "changwon",
}

KBO_VENUE_ROWS = [
    {
        "venue_id": "seoul_jamsil",
        "venue_name": "Seoul-Jamsil",
        "latitude": 37.5122,
        "longitude": 127.0719,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "seoul_gocheok",
        "venue_name": "Seoul-Gocheok",
        "latitude": 37.4982,
        "longitude": 126.8671,
        "timezone_offset": 9,
        "is_dome": 1,
    },
    {
        "venue_id": "incheon_munhak",
        "venue_name": "Incheon-Munhak",
        "latitude": 37.4351,
        "longitude": 126.6908,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "suwon",
        "venue_name": "Suwon",
        "latitude": 37.2998,
        "longitude": 127.0097,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "daejeon",
        "venue_name": "Daejeon",
        "latitude": 36.3170,
        "longitude": 127.4292,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "daegu",
        "venue_name": "Daegu",
        "latitude": 35.8410,
        "longitude": 128.6817,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "gwangju",
        "venue_name": "Gwangju",
        "latitude": 35.1682,
        "longitude": 126.8888,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "busan_sajik",
        "venue_name": "Busan-Sajik",
        "latitude": 35.1940,
        "longitude": 129.0615,
        "timezone_offset": 9,
        "is_dome": 0,
    },
    {
        "venue_id": "changwon",
        "venue_name": "Changwon",
        "latitude": 35.2225,
        "longitude": 128.5822,
        "timezone_offset": 9,
        "is_dome": 0,
    },
]


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


def kbo_venue_seed() -> pd.DataFrame:
    """Return stable KBO venue metadata used by the shared feature builder."""

    return pd.DataFrame(KBO_VENUE_ROWS)


def write_kbo_venue_seed(output: str | Path) -> Path:
    """Write the built-in KBO venue seed table."""

    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    kbo_venue_seed().to_csv(path, index=False)
    return path


def enrich_kbo_games_with_venues(games: pd.DataFrame, venues: pd.DataFrame | None = None) -> pd.DataFrame:
    """Attach KBO venue IDs from MyKBO venue text or the home team's primary park."""

    out = games.copy()
    venue_lookup = (venues.copy() if venues is not None else kbo_venue_seed())
    venue_lookup["venue_name_key"] = venue_lookup["venue_name"].astype(str).str.lower()
    out["venue_id"] = np.nan
    if "venue_name" in out.columns:
        name_key = out["venue_name"].astype(str).str.lower()
        mapping = dict(zip(venue_lookup["venue_name_key"], venue_lookup["venue_id"], strict=False))
        out["venue_id"] = name_key.map(mapping)
    out["venue_id"] = out["venue_id"].fillna(out["home_team"].map(KBO_PRIMARY_VENUES))
    name_by_id = dict(zip(venue_lookup["venue_id"], venue_lookup["venue_name"], strict=False))
    if "venue_name" not in out.columns:
        out["venue_name"] = np.nan
    out["venue_name"] = out["venue_name"].fillna(out["venue_id"].map(name_by_id))
    return out


def augment_kbo_weather_with_open_meteo(
    *,
    games: pd.DataFrame,
    venues: pd.DataFrame | None = None,
    collector=None,
) -> pd.DataFrame:
    """Populate KBO weather rows using Open-Meteo historical hourly data.

    Returns the same column shape as build_kbo_weather_stub but with real
    temperature/wind/humidity for outdoor games. Dome games keep is_dome=1 and
    receive the same outdoor reading (the feature builder can ignore it via the
    dome flag); we do not fabricate indoor air to avoid invented physics.
    """
    from datetime import timedelta

    from mlb_winprob.data_sources import OpenMeteoArchiveCollector

    venue_lookup = (venues.copy() if venues is not None else kbo_venue_seed()).copy()
    venue_lookup["venue_id"] = venue_lookup["venue_id"].astype("string")
    needed = {"venue_id", "latitude", "longitude", "is_dome"}
    missing = needed - set(venue_lookup.columns)
    if missing:
        raise ValueError(f"venues missing columns: {sorted(missing)}")

    collector = collector or OpenMeteoArchiveCollector()
    base = games[["game_id", "game_date", "season", "venue_id"]].copy()
    base["venue_id"] = base["venue_id"].astype("string")
    base["weather_hour"] = pd.to_datetime(base["game_date"], utc=True, errors="coerce").dt.round("h")
    base = base.merge(
        venue_lookup[["venue_id", "latitude", "longitude", "is_dome"]],
        on="venue_id",
        how="left",
    )

    hourly_frames: list[pd.DataFrame] = []
    for (venue_id, season), group in base.dropna(subset=["latitude", "longitude"]).groupby(
        ["venue_id", "season"], dropna=True
    ):
        lat = float(group["latitude"].iloc[0])
        lon = float(group["longitude"].iloc[0])
        min_hour = group["weather_hour"].min()
        max_hour = group["weather_hour"].max()
        if pd.isna(min_hour) or pd.isna(max_hour):
            continue
        hourly = collector.hourly_weather(
            latitude=lat,
            longitude=lon,
            start_date=min_hour.date().isoformat(),
            end_date=(max_hour.date() + timedelta(days=1)).isoformat(),
        )
        hourly["venue_id"] = str(venue_id)
        hourly["season"] = season
        hourly_frames.append(hourly)

    out = base[["game_id", "is_dome"]].copy()
    out["temperature"] = np.nan
    out["wind_speed"] = np.nan
    out["wind_direction"] = np.nan
    out["humidity"] = np.nan
    out["weather_source"] = pd.NA

    if hourly_frames:
        hourly_weather = pd.concat(hourly_frames, ignore_index=True)
        joined = base.merge(hourly_weather, on=["venue_id", "season", "weather_hour"], how="left")
        out["temperature"] = pd.to_numeric(joined["open_meteo_temperature"], errors="coerce").to_numpy()
        out["wind_speed"] = pd.to_numeric(joined["open_meteo_wind_speed"], errors="coerce").to_numpy()
        out["wind_direction"] = pd.to_numeric(joined["open_meteo_wind_direction_degrees"], errors="coerce").to_numpy()
        out["humidity"] = pd.to_numeric(joined["humidity"], errors="coerce").to_numpy()
        out.loc[out["temperature"].notna(), "weather_source"] = "open_meteo_archive"

    out["is_dome"] = pd.to_numeric(out["is_dome"], errors="coerce")
    return out[
        ["game_id", "temperature", "wind_speed", "wind_direction", "humidity", "is_dome", "weather_source"]
    ]


def build_kbo_weather_stub(games: pd.DataFrame, venues: pd.DataFrame | None = None) -> pd.DataFrame:
    """Create offline KBO weather rows with dome status.

    Actual temperature/wind/humidity should come from a later historical weather
    backfill. This keeps the shared weather feature path live without inventing
    outdoor weather observations.
    """

    venue_lookup = (venues.copy() if venues is not None else kbo_venue_seed())[["venue_id", "is_dome"]].copy()
    venue_lookup["venue_id"] = venue_lookup["venue_id"].astype("string")
    out = games[["game_id", "venue_id"]].copy()
    out["venue_id"] = out["venue_id"].astype("string")
    out = out.merge(venue_lookup, on="venue_id", how="left")
    out["temperature"] = np.nan
    out["wind_speed"] = np.nan
    out["wind_direction"] = np.nan
    out["humidity"] = np.nan
    out["is_dome"] = pd.to_numeric(out["is_dome"], errors="coerce")
    return out[["game_id", "temperature", "wind_speed", "wind_direction", "humidity", "is_dome"]]


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
