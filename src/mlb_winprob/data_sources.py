"""Data loading and public-data collection adapters."""

from __future__ import annotations

import os
import json
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

USER_AGENT = "mlb-winprob/0.1.5"
MLB_STATS_API_BASE_URL = "https://statsapi.mlb.com/api/v1"
MLB_STATS_API_FEED_BASE_URL = "https://statsapi.mlb.com/api/v1.1"
OPEN_METEO_ARCHIVE_BASE_URL = "https://archive-api.open-meteo.com/v1"
RETROSHEET_BASE_URL = "https://www.retrosheet.org/downloads"
BASEBALL_DATABANK_BASE_URL = "https://raw.githubusercontent.com/chadwickbureau/baseballdatabank/master/core"
CHADWICK_REGISTER_BASE_URL = "https://raw.githubusercontent.com/chadwickbureau/register/master/data"

RETROSHEET_DOWNLOADS = {
    "main_csv": f"{RETROSHEET_BASE_URL}/csvdownloads.zip",
    "basic_csvs": f"{RETROSHEET_BASE_URL}/basiccsvs.zip",
    "biodata": f"{RETROSHEET_BASE_URL}/biodata.zip",
    "allplayers": f"{RETROSHEET_BASE_URL}/allplayers.csv",
    "gameinfo": f"{RETROSHEET_BASE_URL}/gameinfo.csv",
    "teamstats": f"{RETROSHEET_BASE_URL}/teamstats.csv",
    "batting": f"{RETROSHEET_BASE_URL}/batting.csv",
    "pitching": f"{RETROSHEET_BASE_URL}/pitching.csv",
    "fielding": f"{RETROSHEET_BASE_URL}/fielding.csv",
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
    frame = pd.read_csv(path)
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


def fetch_json(url: str, params: dict[str, str | int | None] | None = None) -> dict:
    """Fetch a JSON endpoint using only the standard library."""

    filtered_params = {key: value for key, value in (params or {}).items() if value is not None}
    full_url = f"{url}?{urlencode(filtered_params)}" if filtered_params else url
    request = Request(full_url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
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


class RetrosheetCollector:
    """Download Retrosheet CSV archives and master CSV files."""

    downloads = RETROSHEET_DOWNLOADS

    def download(self, dataset: str, output: str | Path) -> Path:
        if dataset not in self.downloads:
            valid = ", ".join(sorted(self.downloads))
            raise ValueError(f"Unknown Retrosheet dataset '{dataset}'. Valid values: {valid}")
        return download_url(self.downloads[dataset], output)


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
        return download_url(f"{CHADWICK_REGISTER_BASE_URL}/people.csv", output)


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
