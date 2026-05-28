"""Data loading and public-data collection adapters."""

from __future__ import annotations

import os
import json
import random
import re
import zipfile
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor, as_completed
from io import StringIO
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

USER_AGENT = "mlb-winprob/0.1.5"
MLB_STATS_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
MLB_STATS_API_FEED_BASE_URL = "https://statsapi.mlb.com/api/v1.1"
OPEN_METEO_ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1"
BALLDONTLIE_MLB_API_BASE_URL = "https://api.balldontlie.io/mlb/v1"
MYKBO_STATS_BASE_URL = "https://mykbostats.com"
NPB_OFFICIAL_BASE_URL = "https://npb.jp"
PROEYEKYUU_BASE_URL = "https://proeyekyuu.com"
BASEBALL_DATA_JP_BASE_URL = "https://baseballdata.jp"
RETROSHEET_BASE_URL = "https://www.retrosheet.org/downloads"
BASEBALL_DATABANK_BASE_URL = "https://raw.githubusercontent.com/chadwickbureau/baseballdatabank/master/core"
CHADWICK_REGISTER_BASE_URL = "https://raw.githubusercontent.com/chadwickbureau/register/master/data"
CHADWICK_PEOPLE_SHARDS = tuple("0123456789abcdef")

RETROSHEET_DOWNLOADS = {
    "main_csv": f"{RETROSHEET_BASE_URL}/csvdownloads.zip",
    "basic_csvs": f"{RETROSHEET_BASE_URL}/basiccsvs.zip",
    "biodata": f"{RETROSHEET_BASE_URL}/biodata.zip",
    "allplayers": f"{RETROSHEET_BASE_URL}/allplayers.csv",
    "gameinfo": f"{RETROSHEET_BASE_URL}/gameinfo.zip",
    "teamstats": f"{RETROSHEET_BASE_URL}/teamstats.zip",
    "batting": f"{RETROSHEET_BASE_URL}/batting.zip",
    "pitching": f"{RETROSHEET_BASE_URL}/pitching.zip",
    "fielding": f"{RETROSHEET_BASE_URL}/fielding.zip",
}

LAHMAN_CORE_TABLES = {
    "People",
    "Batting",
    "Pitching",
    "Teams",
    "Fielding",
    "Appearances",
    "Parks",
    "HomeGames",
}

VENUE_COORDINATE_FALLBACKS = {
    # MLB Stats API omits defaultCoordinates for this Mexico City Series venue.
    5340: (19.403611, -99.085278),
}


def read_csv_table(path: str | Path) -> pd.DataFrame:
    frame = pd.read_csv(path, low_memory=False)
    if "game_date" in frame.columns:
        frame["game_date"] = pd.to_datetime(frame["game_date"])
    return frame


def write_csv_table(frame: pd.DataFrame, path: str | Path) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False)


def download_url(url: str, output: str | Path) -> Path:
    """Download a URL to disk without adding project-specific parsing."""

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request) as response, target.open("wb") as file:
        file.write(response.read())
    return target


def fetch_text(url: str, *, headers: dict[str, str] | None = None) -> str:
    """Fetch a text URL with a browser-like default header."""

    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    request_headers.update(headers or {})
    request = Request(url, headers=request_headers)
    with urlopen(request) as response:
        return response.read().decode("utf-8")


def fetch_json(
    url: str,
    params: dict[str, str | int | list[str | int] | None] | None = None,
    *,
    headers: dict[str, str] | None = None,
) -> dict:
    """Fetch a JSON endpoint using only the standard library."""

    filtered_params = {key: value for key, value in (params or {}).items() if value is not None}
    full_url = f"{url}?{urlencode(filtered_params, doseq=True)}" if filtered_params else url
    request_headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    request_headers.update(headers or {})
    request = Request(full_url, headers=request_headers)
    with urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


def write_json(data: dict, path: str | Path) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def default_collection_workers() -> int:
    """Choose a conservative default for network-bound public-data collection."""

    return min(32, max(1, (os.cpu_count() or 1) * 2))


ProgressCallback = Callable[[int, int, int, int], None]


class MLBStatsApiCollector:
    """Collector for MLB Stats API schedule and game-level JSON."""

    def __init__(
        self,
        base_url: str = MLB_STATS_API_BASE_URL,
        feed_base_url: str = MLB_STATS_API_FEED_BASE_URL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.feed_base_url = feed_base_url.rstrip("/")

    def schedule(
        self,
        start_date: str,
        end_date: str,
        *,
        sport_id: int = 1,
        hydrate: str = "probablePitcher,venue,team,linescore",
    ) -> pd.DataFrame:
        payload = fetch_json(
            f"{self.base_url}/schedule",
            {
                "sportId": sport_id,
                "startDate": start_date,
                "endDate": end_date,
                "hydrate": hydrate,
            },
        )
        return self.normalize_schedule(payload)

    def game_feed(self, game_pk: int | str) -> dict:
        return fetch_json(f"{self.feed_base_url}/game/{game_pk}/feed/live")

    def boxscore(self, game_pk: int | str) -> dict:
        return fetch_json(f"{self.base_url}/game/{game_pk}/boxscore")

    def people(self, player_ids: list[int | str], *, chunk_size: int = 100) -> pd.DataFrame:
        rows: list[dict] = []
        normalized_ids = [str(int(float(player_id))) for player_id in player_ids if pd.notna(player_id)]
        seen_ids = sorted(set(normalized_ids), key=int)
        for index in range(0, len(seen_ids), chunk_size):
            chunk = seen_ids[index : index + chunk_size]
            payload = fetch_json(f"{self.base_url}/people", {"personIds": ",".join(chunk)})
            for person in payload.get("people", []):
                rows.append(
                    {
                        "player_id": person.get("id"),
                        "player_name": person.get("fullName"),
                        "bats": (person.get("batSide") or {}).get("code"),
                        "throws": (person.get("pitchHand") or {}).get("code"),
                        "primary_position": (person.get("primaryPosition") or {}).get("abbreviation"),
                    }
                )
        return pd.DataFrame(rows)

    def venues(self, venue_ids: list[int | str]) -> pd.DataFrame:
        rows: list[dict] = []
        normalized_ids = [str(int(float(venue_id))) for venue_id in venue_ids if pd.notna(venue_id)]
        for venue_id in sorted(set(normalized_ids), key=int):
            payload = fetch_json(f"{self.base_url}/venues/{venue_id}", {"hydrate": "location"})
            for venue in payload.get("venues", []) or []:
                location = venue.get("location") or {}
                coordinates = location.get("defaultCoordinates") or {}
                fallback = VENUE_COORDINATE_FALLBACKS.get(int(venue_id))
                latitude = coordinates.get("latitude")
                longitude = coordinates.get("longitude")
                if fallback and (latitude is None or longitude is None):
                    latitude, longitude = fallback
                rows.append(
                    {
                        "venue_id": venue.get("id"),
                        "venue_name": venue.get("name"),
                        "latitude": latitude,
                        "longitude": longitude,
                        "city": location.get("city"),
                        "state": location.get("state"),
                        "country": location.get("country"),
                    }
                )
        return pd.DataFrame(rows)

    def save_boxscores(
        self,
        game_ids: list[int | str],
        output_dir: str | Path,
        *,
        skip_existing: bool = True,
        workers: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[Path]:
        return self._save_game_json_files(
            game_ids,
            output_dir,
            suffix="_boxscore.json",
            fetcher=self.boxscore,
            skip_existing=skip_existing,
            workers=workers,
            progress_callback=progress_callback,
        )

    def save_game_feeds(
        self,
        game_ids: list[int | str],
        output_dir: str | Path,
        *,
        skip_existing: bool = True,
        workers: int | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> list[Path]:
        return self._save_game_json_files(
            game_ids,
            output_dir,
            suffix="_feed.json",
            fetcher=self.game_feed,
            skip_existing=skip_existing,
            workers=workers,
            progress_callback=progress_callback,
        )

    def _save_game_json_files(
        self,
        game_ids: list[int | str],
        output_dir: str | Path,
        *,
        suffix: str,
        fetcher: Callable[[int | str], dict],
        skip_existing: bool,
        workers: int | None,
        progress_callback: ProgressCallback | None,
    ) -> list[Path]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        total = len(game_ids)
        downloaded = 0
        skipped = 0
        failed = 0
        paths_by_game_id: dict[str, Path] = {}
        pending: list[tuple[str, Path]] = []

        for game_id in game_ids:
            normalized_id = str(game_id)
            path = target_dir / f"{normalized_id}{suffix}"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                skipped += 1
                paths_by_game_id[normalized_id] = path
                if progress_callback:
                    progress_callback(downloaded, skipped, failed, total)
                continue
            pending.append((normalized_id, path))

        if not pending:
            return [paths_by_game_id[str(game_id)] for game_id in game_ids]

        max_workers = workers or default_collection_workers()
        if max_workers < 1:
            raise ValueError("workers must be at least 1")

        def collect_one(game_id: str, path: Path) -> tuple[str, Path]:
            payload = fetcher(game_id)
            return game_id, write_json(payload, path)

        errors: list[tuple[str, Exception]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(collect_one, game_id, path): game_id
                for game_id, path in pending
            }
            for future in as_completed(futures):
                game_id = futures[future]
                try:
                    completed_game_id, path = future.result()
                except Exception as exc:
                    failed += 1
                    errors.append((game_id, exc))
                else:
                    downloaded += 1
                    paths_by_game_id[completed_game_id] = path
                if progress_callback:
                    progress_callback(downloaded, skipped, failed, total)

        if errors:
            examples = ", ".join(f"{game_id}: {exc}" for game_id, exc in errors[:3])
            remaining = "" if len(errors) <= 3 else f" (+{len(errors) - 3} more)"
            raise RuntimeError(f"Failed to collect {len(errors)} game JSON files: {examples}{remaining}")

        return [paths_by_game_id[str(game_id)] for game_id in game_ids]

    @staticmethod
    def normalize_schedule(payload: dict) -> pd.DataFrame:
        rows: list[dict] = []
        for date_group in payload.get("dates", []):
            for game in date_group.get("games", []):
                home = game.get("teams", {}).get("home", {})
                away = game.get("teams", {}).get("away", {})
                home_team = home.get("team", {})
                away_team = away.get("team", {})
                venue = game.get("venue", {})
                rows.append(
                    {
                        "game_id": game.get("gamePk"),
                        "game_date": game.get("gameDate") or date_group.get("date"),
                        "season": game.get("season"),
                        "game_type": game.get("gameType"),
                        "status": game.get("status", {}).get("detailedState"),
                        "home_team_id": home_team.get("id"),
                        "home_team": home_team.get("name"),
                        "home_team_abbrev": home_team.get("abbreviation"),
                        "away_team_id": away_team.get("id"),
                        "away_team": away_team.get("name"),
                        "away_team_abbrev": away_team.get("abbreviation"),
                        "home_score": home.get("score"),
                        "away_score": away.get("score"),
                        "home_sp_id": home.get("probablePitcher", {}).get("id"),
                        "home_sp_name": home.get("probablePitcher", {}).get("fullName"),
                        "away_sp_id": away.get("probablePitcher", {}).get("id"),
                        "away_sp_name": away.get("probablePitcher", {}).get("fullName"),
                        "venue_id": venue.get("id"),
                        "venue_name": venue.get("name"),
                    }
                )
        frame = pd.DataFrame(rows)
        if "game_date" in frame.columns:
            frame["game_date"] = pd.to_datetime(frame["game_date"], errors="coerce")
        return frame


def _first_present(mapping: dict, keys: list[str]) -> object:
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return None


def _extract_lineup_player_rows(lineup: dict) -> list[dict]:
    for key in ["players", "batters", "lineup", "starting_lineup"]:
        value = lineup.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    for key in ["home", "away", "team"]:
        value = lineup.get(key)
        if isinstance(value, dict):
            rows = _extract_lineup_player_rows(value)
            if rows:
                return rows
    return []


class BallDontLieMLBCollector:
    """Collector and normalizer for BALLDONTLIE MLB projected lineup snapshots."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = BALLDONTLIE_MLB_API_BASE_URL,
    ) -> None:
        self.api_key = api_key or os.environ.get("BALLDONTLIE_API_KEY")
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": self.api_key} if self.api_key else {}

    def lineups(
        self,
        *,
        game_ids: list[int | str] | None = None,
        dates: list[str] | None = None,
        per_page: int = 100,
    ) -> dict:
        """Fetch raw lineup payloads, preserving provider JSON shape."""

        params: dict[str, str | int | list[str | int] | None] = {"per_page": per_page}
        if game_ids:
            params["game_ids[]"] = [str(game_id) for game_id in game_ids]
        if dates:
            params["dates[]"] = dates

        all_items: list[dict] = []
        cursor: str | int | None = None
        meta: dict = {}
        while True:
            if cursor is not None:
                params["cursor"] = cursor
            payload = fetch_json(f"{self.base_url}/lineups", params, headers=self._headers())
            data = payload.get("data", [])
            if isinstance(data, list):
                all_items.extend(item for item in data if isinstance(item, dict))
            meta = payload.get("meta") or {}
            cursor = meta.get("next_cursor")
            if not cursor:
                break
        return {"data": all_items, "meta": meta}

    def save_lineups(
        self,
        output: str | Path,
        *,
        game_ids: list[int | str] | None = None,
        dates: list[str] | None = None,
        per_page: int = 100,
    ) -> Path:
        payload = self.lineups(game_ids=game_ids, dates=dates, per_page=per_page)
        return write_json(payload, output)

    @staticmethod
    def normalize_lineups(
        payload: dict,
        *,
        captured_at: str | None = None,
        prediction_mode: str = "projected",
        game_id_map: pd.DataFrame | None = None,
        player_id_map: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        """Convert provider lineup JSON into the project's standard lineups rows.

        BALLDONTLIE provider IDs are kept as external IDs. Optional maps can
        translate them to MLBAM game/player IDs used by this project's feature
        tables.
        """

        game_lookup = _external_lookup(game_id_map, "external_game_id", "game_id")
        player_lookup = _external_lookup(player_id_map, "external_player_id", "player_id")
        rows: list[dict[str, object]] = []
        for lineup in payload.get("data", []) or []:
            if not isinstance(lineup, dict):
                continue
            external_game_id = _first_present(
                lineup,
                ["game_id", "gameId", "game", "id", "external_game_id"],
            )
            if isinstance(external_game_id, dict):
                external_game_id = _first_present(external_game_id, ["id"])
            game_value = lineup.get("game") if isinstance(lineup.get("game"), dict) else {}
            game_date = _first_present(lineup, ["game_date", "date", "scheduled_at"])
            if game_date is None and isinstance(game_value, dict):
                game_date = _first_present(game_value, ["date", "game_date", "datetime", "scheduled_at"])
            home_team = _first_present(lineup, ["home_team", "home_team_abbreviation"])
            away_team = _first_present(lineup, ["away_team", "away_team_abbreviation"])
            if isinstance(game_value, dict):
                home_value = game_value.get("home_team") or game_value.get("home")
                away_value = game_value.get("away_team") or game_value.get("away")
                if home_team is None and isinstance(home_value, dict):
                    home_team = _first_present(home_value, ["abbreviation", "abbr", "name", "full_name"])
                elif home_team is None:
                    home_team = home_value
                if away_team is None and isinstance(away_value, dict):
                    away_team = _first_present(away_value, ["abbreviation", "abbr", "name", "full_name"])
                elif away_team is None:
                    away_team = away_value
            game_id = game_lookup.get(str(external_game_id), external_game_id)
            team_value = _first_present(lineup, ["team_abbreviation", "team_abbrev", "team", "team_name"])
            if isinstance(team_value, dict):
                team_value = _first_present(team_value, ["abbreviation", "abbr", "name", "full_name", "id"])
            lineup_status = _first_present(lineup, ["status", "lineup_status", "type"])

            for player_row in _extract_lineup_player_rows(lineup):
                player = player_row.get("player") if isinstance(player_row.get("player"), dict) else player_row
                external_player_id = _first_present(
                    player,
                    ["id", "player_id", "playerId", "external_player_id"],
                )
                player_id = player_lookup.get(str(external_player_id), external_player_id)
                batting_order = _first_present(
                    player_row,
                    ["batting_order", "battingOrder", "order", "lineup_position", "slot"],
                )
                position = _first_present(player_row, ["position", "pos"])
                if isinstance(position, dict):
                    position = _first_present(position, ["abbreviation", "name"])
                rows.append(
                    {
                        "game_id": game_id,
                        "team": team_value,
                        "player_id": player_id,
                        "player_name": _first_present(player, ["full_name", "name", "display_name"]),
                        "batting_order": batting_order,
                        "position": position,
                        "bats": _first_present(player, ["bats", "bat_side", "batSide"]),
                        "prediction_mode": prediction_mode,
                        "lineup_source": "balldontlie_mlb",
                        "lineup_confidence": 0.65,
                        "is_available": 1.0,
                        "is_expected_starter": 1.0,
                        "captured_at": captured_at or _first_present(lineup, ["captured_at", "updated_at"]),
                        "provider_lineup_status": lineup_status,
                        "external_game_id": external_game_id,
                        "external_player_id": external_player_id,
                        "game_date": game_date,
                        "home_team": home_team,
                        "away_team": away_team,
                    }
                )
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame["batting_order"] = pd.to_numeric(frame["batting_order"], errors="coerce")
            frame = frame.dropna(subset=["game_id", "team", "player_id", "batting_order"])
            frame = frame.sort_values(["game_id", "team", "batting_order", "player_id"]).reset_index(drop=True)
        return frame


def _external_lookup(frame: pd.DataFrame | None, external_column: str, target_column: str) -> dict[str, object]:
    if frame is None or frame.empty:
        return {}
    if external_column not in frame.columns or target_column not in frame.columns:
        raise ValueError(f"Mapping file must contain {external_column} and {target_column}")
    out: dict[str, object] = {}
    for _, row in frame[[external_column, target_column]].dropna().iterrows():
        out[str(row[external_column])] = row[target_column]
    return out


class RetrosheetCollector:
    """Download Retrosheet CSV archives and master CSV files."""

    downloads = RETROSHEET_DOWNLOADS

    def download(self, dataset: str, output: str | Path) -> Path:
        if dataset not in self.downloads:
            valid = ", ".join(sorted(self.downloads))
            raise ValueError(f"Unknown Retrosheet dataset '{dataset}'. Valid values: {valid}")
        url = self.downloads[dataset]
        output_path = Path(output)
        if url.endswith(".zip") and output_path.suffix.lower() == ".csv":
            zip_path = output_path.with_suffix(".zip")
            download_url(url, zip_path)
            with zipfile.ZipFile(zip_path) as archive:
                csv_members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
                if not csv_members:
                    raise ValueError(f"No CSV files found in {zip_path}")
                preferred = f"{dataset}.csv"
                member = preferred if preferred in csv_members else csv_members[0]
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, output_path.open("wb") as target:
                    target.write(source.read())
            return output_path
        return download_url(url, output_path)


class LahmanCollector:
    """Download Lahman/Baseball Databank CSV tables from Chadwick Bureau."""

    def download_table(self, table: str, output: str | Path) -> Path:
        normalized = table.strip()
        if normalized not in LAHMAN_CORE_TABLES:
            valid = ", ".join(sorted(LAHMAN_CORE_TABLES))
            raise ValueError(f"Unknown Lahman table '{table}'. Valid values: {valid}")
        return download_url(f"{BASEBALL_DATABANK_BASE_URL}/{normalized}.csv", output)

    def download_archive(self, output: str | Path) -> Path:
        return download_url("https://github.com/chadwickbureau/baseballdatabank/archive/master.zip", output)


class ChadwickRegisterCollector:
    """Download Chadwick Bureau player ID register tables."""

    def download_people(self, output: str | Path) -> Path:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        frames = []
        for shard in CHADWICK_PEOPLE_SHARDS:
            shard_path = output_path.with_name(f"people-{shard}.csv")
            download_url(f"{CHADWICK_REGISTER_BASE_URL}/people-{shard}.csv", shard_path)
            frames.append(pd.read_csv(shard_path, low_memory=False))
        pd.concat(frames, ignore_index=True).to_csv(output_path, index=False)
        return output_path


class OpenMeteoArchiveCollector:
    """Collector for Open-Meteo historical hourly weather."""

    def __init__(self, base_url: str = OPEN_METEO_ARCHIVE_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def hourly_weather(
        self,
        *,
        latitude: float,
        longitude: float,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        payload = fetch_json(
            f"{self.base_url}/archive",
            {
                "latitude": latitude,
                "longitude": longitude,
                "start_date": start_date,
                "end_date": end_date,
                "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,wind_direction_10m",
                "temperature_unit": "fahrenheit",
                "wind_speed_unit": "mph",
                "timezone": "UTC",
            },
        )
        hourly = payload.get("hourly") or {}
        return pd.DataFrame(
            {
                "weather_hour": pd.to_datetime(hourly.get("time", []), utc=True),
                "open_meteo_temperature": hourly.get("temperature_2m", []),
                "humidity": hourly.get("relative_humidity_2m", []),
                "open_meteo_wind_speed": hourly.get("wind_speed_10m", []),
                "open_meteo_wind_direction_degrees": hourly.get("wind_direction_10m", []),
            }
        )


class PyBaseballCollector:
    """Thin optional adapter for public pybaseball pulls.

    The modeling pipeline does not depend on this class. It exists so raw data
    collection can be swapped or extended without changing feature generation.
    """

    def __init__(self) -> None:
        try:
            import pybaseball as pybaseball_module
        except ImportError as exc:
            raise RuntimeError("Install the data extra first: pip install -e '.[data]'") from exc
        self.pybaseball = pybaseball_module

    def statcast(self, start_date: str, end_date: str) -> pd.DataFrame:
        return self.pybaseball.statcast(start_dt=start_date, end_dt=end_date)

    def batting_stats(self, season: int) -> pd.DataFrame:
        return self.pybaseball.batting_stats(season)

    def pitching_stats(self, season: int) -> pd.DataFrame:
        return self.pybaseball.pitching_stats(season)

    def statcast_batter(self, start_date: str, end_date: str, player_id: int) -> pd.DataFrame:
        return self.pybaseball.statcast_batter(start_date, end_date, player_id)

    def statcast_pitcher(self, start_date: str, end_date: str, player_id: int) -> pd.DataFrame:
        return self.pybaseball.statcast_pitcher(start_date, end_date, player_id)


class MyKBOStatsCollector:
    """Collector for public MyKBO Stats pages.

    MyKBO is a secondary, unofficial source. This collector intentionally saves
    raw HTML alongside parsed tables so parser changes can be audited.
    """

    PAGE_PATHS = {
        "stats": "/stats/{season}",
        "batting_ops": "/stats/top/ops/{season}",
        "pitching_era": "/stats/top/era/{season}",
        "team_splits": "/stats/team_splits/{season}",
        "park_splits": "/stats/park_splits/{season}",
        "schedule": "/schedule/{season}",
        "foreign_players": "/players/foreign/{season}",
    }

    def __init__(self, base_url: str = MYKBO_STATS_BASE_URL) -> None:
        self.base_url = base_url.rstrip("/")

    def page_url(self, page: str, season: int) -> str:
        if page not in self.PAGE_PATHS:
            valid = ", ".join(sorted(self.PAGE_PATHS))
            raise ValueError(f"Unknown MyKBO page '{page}'. Valid values: {valid}")
        return f"{self.base_url}{self.PAGE_PATHS[page].format(season=season)}"

    def fetch_page(self, page: str, season: int) -> str:
        return self.fetch_url(self.page_url(page, season))

    def fetch_url(self, url: str, *, max_retries: int = 5) -> str:
        try:
            import requests
        except ImportError:
            return fetch_text(url, headers=self._headers())

        import time

        backoff = 5.0
        for attempt in range(max_retries):
            response = requests.get(url, headers=self._headers(), timeout=30)
            if response.status_code == 429 and attempt < max_retries - 1:
                # Respect Retry-After when present, otherwise exponential backoff.
                retry_after = response.headers.get("Retry-After")
                wait = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                time.sleep(wait)
                backoff = min(backoff * 2, 60.0)
                continue
            response.raise_for_status()
            return response.text
        response.raise_for_status()
        return response.text

    def save_page(self, page: str, season: int, output: str | Path) -> Path:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        html = self.fetch_page(page, season)
        target.write_text(html, encoding="utf-8")
        return target

    def save_season_pages(
        self,
        season: int,
        output_dir: str | Path,
        *,
        pages: list[str] | None = None,
        skip_existing: bool = True,
    ) -> list[Path]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for page in pages or list(self.PAGE_PATHS):
            path = target_dir / f"{page}_{season}.html"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                saved.append(path)
                continue
            saved.append(self.save_page(page, season, path))
        return saved

    def schedule_week_url(self, week_of: str) -> str:
        return f"{self.base_url}/schedule/week_of/{week_of}"

    def save_schedule_weeks(
        self,
        start_date: str,
        end_date: str,
        output_dir: str | Path,
        *,
        skip_existing: bool = True,
    ) -> list[Path]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        dates = pd.date_range(start=start_date, end=end_date, freq="7D")
        saved: list[Path] = []
        for date in dates:
            date_text = date.date().isoformat()
            path = target_dir / f"schedule_week_of_{date_text}.html"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                saved.append(path)
                continue
            html = self.fetch_url(self.schedule_week_url(date_text))
            path.write_text(html, encoding="utf-8")
            saved.append(path)
        return saved

    def save_game_pages(
        self,
        games: pd.DataFrame,
        output_dir: str | Path,
        *,
        limit: int | None = None,
        skip_existing: bool = True,
        delay: float = 0.0,
        max_workers: int = 1,
    ) -> list[Path]:
        if "source_href" not in games.columns:
            raise ValueError("games must include source_href")
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        rows = games.dropna(subset=["source_href"]).copy()
        rows = rows[rows["source_href"].astype(str).str.contains(r"^/games/\d+-", regex=True, na=False)]
        if limit:
            rows = rows.head(limit)

        # Build the ordered work list, separating already-saved pages from those to fetch.
        plan: list[tuple[int, Path, str | None]] = []
        for position, (_, row) in enumerate(rows.iterrows()):
            href = str(row["source_href"])
            match = re.search(r"/games/(\d+)-", href)
            game_id = str(row.get("game_id") or (match.group(1) if match else position))
            path = target_dir / f"{game_id}_game.html"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                plan.append((position, path, None))
                continue
            url = href if href.startswith("http") else f"{self.base_url}{href}"
            plan.append((position, path, url))

        import time

        def _fetch(path: Path, url: str) -> Path:
            if delay > 0:
                # Jitter avoids hammering the source in lockstep across workers.
                time.sleep(delay * (0.5 + random.random()))
            html = self.fetch_url(url)
            path.write_text(html, encoding="utf-8")
            return path

        results: dict[int, Path] = {}
        pending = [(position, path, url) for position, path, url in plan if url is not None]
        # Record already-present (skipped) pages directly.
        for position, path, url in plan:
            if url is None:
                results[position] = path

        if pending:
            workers = max(1, max_workers)
            if workers == 1:
                for position, path, url in pending:
                    results[position] = _fetch(path, url)
            else:
                with ThreadPoolExecutor(max_workers=workers) as executor:
                    futures = {executor.submit(_fetch, path, url): position for position, path, url in pending}
                    for future in as_completed(futures):
                        results[futures[future]] = future.result()

        return [results[position] for position, _, _ in plan]

    @staticmethod
    def parse_html_tables(html: str) -> list[pd.DataFrame]:
        try:
            return pd.read_html(StringIO(html), flavor="lxml")
        except (ImportError, ValueError):
            return []

    @staticmethod
    def extract_links(html: str) -> pd.DataFrame:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return pd.DataFrame(columns=["text", "href"])

        soup = BeautifulSoup(html, "lxml")
        rows = []
        for link in soup.find_all("a"):
            href = link.get("href")
            text = " ".join(link.get_text(" ", strip=True).split())
            if href:
                rows.append({"text": text, "href": href})
        return pd.DataFrame(rows)

    @staticmethod
    def extract_schedule_text(html: str) -> pd.DataFrame:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return pd.DataFrame(columns=["line_number", "text"])

        soup = BeautifulSoup(html, "lxml")
        main = soup.find("main") or soup.find("body")
        if main is None:
            return pd.DataFrame(columns=["line_number", "text"])
        lines = [
            " ".join(line.split())
            for line in main.get_text("\n", strip=True).splitlines()
            if " ".join(line.split())
        ]
        return pd.DataFrame({"line_number": range(1, len(lines) + 1), "text": lines})

    @staticmethod
    def write_html_tables(html_path: str | Path, output_dir: str | Path) -> list[Path]:
        source = Path(html_path)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        html = source.read_text(encoding="utf-8")
        paths: list[Path] = []
        for index, table in enumerate(MyKBOStatsCollector.parse_html_tables(html), start=1):
            output = target_dir / f"{source.stem}_table_{index}.csv"
            table.to_csv(output, index=False)
            paths.append(output)
        links = MyKBOStatsCollector.extract_links(html)
        if not links.empty:
            output = target_dir / f"{source.stem}_links.csv"
            links.to_csv(output, index=False)
            paths.append(output)
        schedule_text = MyKBOStatsCollector.extract_schedule_text(html)
        if not schedule_text.empty and "schedule" in source.stem:
            output = target_dir / f"{source.stem}_text.csv"
            schedule_text.to_csv(output, index=False)
            paths.append(output)
        return paths

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            ),
            "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        }


class PublicHtmlTableCollector:
    """Small collector for public HTML pages with tabular baseball data."""

    PAGE_PATHS: dict[str, str] = {}

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def page_url(self, page: str, season: int | None = None) -> str:
        if page not in self.PAGE_PATHS:
            valid = ", ".join(sorted(self.PAGE_PATHS))
            raise ValueError(f"Unknown page '{page}'. Valid values: {valid}")
        path = self.PAGE_PATHS[page].format(season=season or "")
        return path if path.startswith("http") else f"{self.base_url}{path}"

    def fetch_page(self, page: str, season: int | None = None) -> str:
        return fetch_text(self.page_url(page, season), headers=self._headers())

    def save_page(self, page: str, output: str | Path, *, season: int | None = None) -> Path:
        target = Path(output)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(self.fetch_page(page, season), encoding="utf-8")
        return target

    def save_pages(
        self,
        output_dir: str | Path,
        *,
        pages: list[str] | None = None,
        season: int | None = None,
        skip_existing: bool = True,
    ) -> list[Path]:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        saved: list[Path] = []
        for page in pages or list(self.PAGE_PATHS):
            suffix = f"_{season}" if season is not None else ""
            path = target_dir / f"{page}{suffix}.html"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                saved.append(path)
                continue
            saved.append(self.save_page(page, path, season=season))
        return saved

    @staticmethod
    def parse_html_tables(html: str) -> list[pd.DataFrame]:
        try:
            return pd.read_html(StringIO(html), flavor="lxml")
        except (ImportError, ValueError):
            return []

    @staticmethod
    def extract_links(html: str) -> pd.DataFrame:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return pd.DataFrame(columns=["text", "href"])

        soup = BeautifulSoup(html, "lxml")
        rows = []
        for link in soup.find_all("a"):
            href = link.get("href")
            text = " ".join(link.get_text(" ", strip=True).split())
            if href:
                rows.append({"text": text, "href": href})
        return pd.DataFrame(rows)

    @staticmethod
    def extract_dynamic_tables(html: str) -> pd.DataFrame:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return pd.DataFrame(columns=["table_id", "filter_labels"])

        soup = BeautifulSoup(html, "lxml")
        rows = []
        for wrapper in soup.select("[data-wpdatatable_id]"):
            labels = [
                " ".join(label.get_text(" ", strip=True).replace(":", "").split())
                for label in wrapper.select(".wpDataTableFilterSection label")
            ]
            rows.append(
                {
                    "table_id": wrapper.get("data-wpdatatable_id"),
                    "filter_labels": "|".join(label for label in labels if label),
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def extract_iframes(html: str) -> pd.DataFrame:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return pd.DataFrame(columns=["iframe_id", "title", "src"])

        soup = BeautifulSoup(html, "lxml")
        rows = []
        for iframe in soup.find_all("iframe"):
            src = iframe.get("src")
            if src:
                rows.append(
                    {
                        "iframe_id": iframe.get("id"),
                        "title": iframe.get("title"),
                        "src": src,
                    }
                )
        return pd.DataFrame(rows)

    @staticmethod
    def extract_static_html_tables(html: str) -> list[pd.DataFrame]:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return []

        soup = BeautifulSoup(html, "lxml")
        frames: list[pd.DataFrame] = []
        for table in soup.find_all("table"):
            headers = [" ".join(header.get_text(" ", strip=True).split()) for header in table.find_all("th")]
            if not headers:
                continue
            normalized_headers = []
            seen_headers: dict[str, int] = {}
            for index, header in enumerate(headers, start=1):
                base = header if header else f"column_{index}"
                count = seen_headers.get(base, 0) + 1
                seen_headers[base] = count
                normalized_headers.append(base if count == 1 else f"{base}_{count}")
            rows = []
            for tr in table.find_all("tr"):
                cells = [" ".join(cell.get_text(" ", strip=True).split()) for cell in tr.find_all("td")]
                if len(cells) == len(normalized_headers):
                    rows.append(cells)
            if rows:
                frames.append(pd.DataFrame(rows, columns=normalized_headers))
        return frames

    @classmethod
    def write_html_tables(cls, html_path: str | Path, output_dir: str | Path) -> list[Path]:
        source = Path(html_path)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        html = source.read_text(encoding="utf-8")
        paths: list[Path] = []
        tables = cls.parse_html_tables(html)
        if not tables:
            tables = cls.extract_static_html_tables(html)
        for index, table in enumerate(tables, start=1):
            output = target_dir / f"{source.stem}_table_{index}.csv"
            table.to_csv(output, index=False)
            paths.append(output)
        links = cls.extract_links(html)
        if not links.empty:
            output = target_dir / f"{source.stem}_links.csv"
            links.to_csv(output, index=False)
            paths.append(output)
        dynamic_tables = cls.extract_dynamic_tables(html)
        if not dynamic_tables.empty:
            output = target_dir / f"{source.stem}_dynamic_tables.csv"
            dynamic_tables.to_csv(output, index=False)
            paths.append(output)
        iframes = cls.extract_iframes(html)
        if not iframes.empty:
            output = target_dir / f"{source.stem}_iframes.csv"
            iframes.to_csv(output, index=False)
            paths.append(output)
        return paths

    @staticmethod
    def _headers() -> dict[str, str]:
        return MyKBOStatsCollector._headers()


class NPBOfficialCollector(PublicHtmlTableCollector):
    """Collector for official NPB public pages used as source-of-truth checks."""

    PAGE_PATHS = {
        "home": "/eng/",
        "abbreviations": "/eng/home/abbreviations.html",
        "teams": "/eng/teams/",
        "players": "/eng/players/",
        "schedule_scores": "/eng/schedule/",
        "standings": "/eng/standings/",
        "stats": "/eng/bis/{season}/stats/",
    }

    def __init__(self, base_url: str = NPB_OFFICIAL_BASE_URL) -> None:
        super().__init__(base_url)


class ProEyeKyuuCollector(PublicHtmlTableCollector):
    """Collector for ProEyeKyuu downloadable NPB tables."""

    GAME_RESULTS_COLUMNS = [
        "GameIDHA",
        "GameID",
        "Season",
        "Date",
        "Game Type",
        "TeamLogoUrl",
        "Team",
        "Home or Away",
        "Result",
        "Score",
        "Other Team",
        "OtherTeamLogoUrl",
        "R",
        "H",
        "E",
        "Box Score",
        "Matchup",
        "Ballpark",
        "Game Start",
        "Game Length",
        "Audience",
        "GameIDLink",
    ]

    PAGE_PATHS = {
        "csvs": "/csvs/",
        "player_registry": "/player-registry/",
        "game_results": "/game-results-table/",
        "game_results_dashboard": "/game-results/",
        "player_batting_stats": "/player-batting-stats/",
        "player_pitching_stats": "/player-pitching-stats/",
        "player_fielding_stats": "/player-fielding-stats/",
        "team_batting_stats": "/team-batting-stats/",
        "team_pitching_stats": "/team-pitching-stats/",
        "team_fielding_stats": "/team-fielding-stats/",
    }

    def __init__(self, base_url: str = PROEYEKYUU_BASE_URL) -> None:
        super().__init__(base_url)

    def game_url(self, game_id: str) -> str:
        return f"{self.base_url}/game/?GameID={game_id}"

    @staticmethod
    def _strip_html(value: object) -> object:
        if not isinstance(value, str):
            return value
        return re.sub(r"<[^>]+>", "", value).strip()

    @classmethod
    def _game_results_request_payload(
        cls,
        *,
        nonce: str,
        season: int,
        start: int = 0,
        length: int = 1000,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "draw": 1,
            "start": start,
            "length": length,
            "search[value]": "",
            "search[regex]": "false",
            "wdtNonce": nonce,
            "showAllRows": "false",
            "order[0][column]": 3,
            "order[0][dir]": "desc",
        }
        for index, column in enumerate(cls.GAME_RESULTS_COLUMNS):
            payload[f"columns[{index}][data]"] = str(index)
            payload[f"columns[{index}][name]"] = column
            payload[f"columns[{index}][searchable]"] = "true"
            payload[f"columns[{index}][orderable]"] = "true"
            payload[f"columns[{index}][search][value]"] = ""
            payload[f"columns[{index}][search][regex]"] = "false"
        payload["columns[2][search][value]"] = str(season)
        return payload

    def fetch_game_results(self, season: int, *, page_length: int = 1000) -> pd.DataFrame:
        """Fetch one season from the ProEyeKyuu server-side game-results table."""

        import requests

        session = requests.Session()
        page_headers = self._headers()
        ajax_headers = {
            **self._headers(),
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": self.page_url("game_results"),
            "X-Requested-With": "XMLHttpRequest",
        }
        page = session.get(self.page_url("game_results"), headers=page_headers, timeout=30)
        page.raise_for_status()
        match = re.search(r'id="wdtNonceFrontendServerSide_25"[^>]*value="([^"]+)"', page.text)
        if not match:
            raise ValueError("Could not find ProEyeKyuu game-results nonce")
        nonce = match.group(1)

        rows: list[list[object]] = []
        records_filtered: int | None = None
        start = 0
        endpoint = f"{self.base_url}/wp-admin/admin-ajax.php?action=get_wdtable&table_id=25"
        while records_filtered is None or start < records_filtered:
            payload = self._game_results_request_payload(
                nonce=nonce,
                season=season,
                start=start,
                length=page_length,
            )
            response = session.post(endpoint, data=payload, headers=ajax_headers, timeout=60)
            response.raise_for_status()
            data = response.json()
            records_filtered = int(data.get("recordsFiltered") or 0)
            batch = data.get("data") or []
            if not batch:
                break
            rows.extend(batch)
            start += len(batch)

        frame = pd.DataFrame(rows, columns=self.GAME_RESULTS_COLUMNS[: len(self.GAME_RESULTS_COLUMNS)])
        for column in frame.select_dtypes(include="object").columns:
            frame[column] = frame[column].map(self._strip_html)
        if "Season" in frame.columns:
            frame["Season"] = pd.to_numeric(frame["Season"], errors="coerce").astype("Int64")
        if "Date" in frame.columns:
            frame["Date"] = pd.to_datetime(frame["Date"], errors="coerce").dt.strftime("%Y-%m-%d")
        return frame

    def save_game_results(
        self,
        output: str | Path,
        *,
        seasons: Iterable[int],
        end_date: str | None = None,
        page_length: int = 1000,
    ) -> Path:
        frames = [self.fetch_game_results(season, page_length=page_length) for season in seasons]
        combined = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=self.GAME_RESULTS_COLUMNS)
        if end_date and "Date" in combined.columns:
            dates = pd.to_datetime(combined["Date"], errors="coerce")
            combined = combined[dates.le(pd.Timestamp(end_date))].copy()
        path = Path(output)
        write_csv_table(combined, path)
        return path

    def save_game_pages(
        self,
        games: pd.DataFrame,
        output_dir: str | Path,
        *,
        limit: int | None = None,
        skip_existing: bool = True,
        workers: int = 1,
    ) -> list[Path]:
        if "game_id" not in games.columns:
            raise ValueError("games must include game_id")
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        rows = games.dropna(subset=["game_id"]).copy()
        if limit:
            rows = rows.head(limit)
        game_ids = rows["game_id"].astype(str).tolist()

        def save_one(game_id: str) -> Path:
            path = target_dir / f"{game_id}_game.html"
            if skip_existing and path.exists() and path.stat().st_size > 0:
                return path
            path.write_text(fetch_text(self.game_url(game_id), headers=self._headers()), encoding="utf-8")
            return path

        if workers <= 1:
            return [save_one(game_id) for game_id in game_ids]

        saved: list[Path] = []
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(save_one, game_id): game_id for game_id in game_ids}
            for future in as_completed(futures):
                saved.append(future.result())
        return sorted(saved)


class BaseballDataJPCollector(PublicHtmlTableCollector):
    """Collector for BaseballData.jp NPB analysis pages."""

    PAGE_PATHS = {
        "home": "/en/",
        "central": "/en/c/",
        "pacific": "/en/p/",
        "central_batting_leaders": "/en/{season}/ctop.html",
        "central_pitching_leaders": "/en/{season}/cptop.html",
        "pacific_batting_leaders": "/en/{season}/ptop.html",
        "pacific_pitching_leaders": "/en/{season}/pptop.html",
    }

    def __init__(self, base_url: str = BASEBALL_DATA_JP_BASE_URL) -> None:
        super().__init__(base_url)
