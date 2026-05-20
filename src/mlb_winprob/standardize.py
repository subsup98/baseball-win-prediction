"""Convert collected source data into the project standard raw CSV schema."""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table


def baseball_innings_to_float(value: object) -> float:
    """Convert baseball innings notation to decimal innings.

    MLB boxscores write one out as `.1` and two outs as `.2`; these are thirds,
    not decimal tenths.
    """

    if value is None or pd.isna(value):
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    if "." not in text:
        return float(text)
    whole, fraction = text.split(".", 1)
    outs = int(fraction[:1] or 0)
    return float(int(whole or 0) + outs / 3)


def _stat(stats: dict, key: str, default: int | float = 0) -> int | float:
    value = stats.get(key, default)
    if value in ("-.--", ".---", "", None):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default


def _player_key(player_id: int | str) -> str:
    return f"ID{player_id}"


def _boxscore_game_id(path: Path) -> str:
    return path.name.split("_", 1)[0]


def _info_map(boxscore: dict) -> dict[str, str]:
    values = {}
    for entry in boxscore.get("info", []) or []:
        label = entry.get("label")
        value = entry.get("value")
        if label and value:
            values[str(label)] = str(value)
    return values


def _parse_humidity(text: str) -> float:
    patterns = [
        r"humidity[:\s]+(\d{1,3})\s*%",
        r"(\d{1,3})\s*%\s*humidity",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            value = int(match.group(1))
            if 0 <= value <= 100:
                return float(value)
    return np.nan


def _parse_weather(info: dict[str, str]) -> dict[str, object]:
    weather = info.get("Weather", "")
    wind = info.get("Wind", "")
    combined = f"{weather} {wind}".strip()

    temperature = np.nan
    match = re.search(r"(\d+)\s+degrees", weather)
    if match:
        temperature = int(match.group(1))

    weather_condition = np.nan
    if "," in weather:
        weather_condition = weather.split(",", 1)[1].strip().rstrip(".") or np.nan

    wind_speed = np.nan
    wind_direction = np.nan
    match = re.search(r"(\d+)\s+mph,?\s*(.*)", wind)
    if match:
        wind_speed = int(match.group(1))
        parsed_direction = match.group(2).strip().rstrip(".")
        wind_direction = parsed_direction if parsed_direction and parsed_direction.lower() != "none" else np.nan

    indoor_markers = ("roof closed", "dome", "indoors", "indoor")
    is_dome = int(any(marker in combined.lower() for marker in indoor_markers)) if combined else np.nan

    return {
        "temperature": temperature,
        "wind_speed": wind_speed,
        "wind_direction": wind_direction,
        "humidity": _parse_humidity(combined),
        "is_dome": is_dome,
        "weather_condition": weather_condition,
        "weather_source": "mlb_stats_api_boxscore" if combined else np.nan,
    }


def _normalize_batting_row(
    *,
    game_id: str,
    game_date: object,
    season: int,
    team: str,
    player: dict,
    opposing_pitcher_hand: object = np.nan,
) -> dict[str, object] | None:
    batting = player.get("stats", {}).get("batting", {})
    if not batting:
        return None
    person = player.get("person", {})
    hits = _stat(batting, "hits")
    doubles = _stat(batting, "doubles")
    triples = _stat(batting, "triples")
    home_runs = _stat(batting, "homeRuns")
    return {
        "game_id": game_id,
        "game_date": game_date,
        "season": season,
        "player_id": person.get("id"),
        "player_name": person.get("fullName"),
        "team": team,
        "opposing_pitcher_hand": opposing_pitcher_hand,
        "at_bats": _stat(batting, "atBats"),
        "hits": hits,
        "doubles": doubles,
        "triples": triples,
        "home_runs": home_runs,
        "walks": _stat(batting, "baseOnBalls"),
        "hit_by_pitch": _stat(batting, "hitByPitch"),
        "sacrifice_flies": _stat(batting, "sacFlies"),
        "total_bases": _stat(batting, "totalBases", hits + doubles + 2 * triples + 3 * home_runs),
        "plate_appearances": _stat(batting, "plateAppearances"),
    }


def _normalize_pitching_row(
    *,
    game_id: str,
    game_date: object,
    season: int,
    team: str,
    player: dict,
    starter_ids: set[int],
) -> dict[str, object] | None:
    pitching = player.get("stats", {}).get("pitching", {})
    if not pitching:
        return None
    person = player.get("person", {})
    player_id = person.get("id")
    innings = baseball_innings_to_float(pitching.get("inningsPitched"))
    games_started = _stat(pitching, "gamesStarted")
    saves = _stat(pitching, "saves")
    holds = _stat(pitching, "holds")
    blown_saves = _stat(pitching, "blownSaves")
    save_opportunities = _stat(pitching, "saveOpportunities")
    games_finished = _stat(pitching, "gamesFinished")
    is_start = int(player_id in starter_ids or games_started > 0)
    return {
        "game_id": game_id,
        "game_date": game_date,
        "season": season,
        "player_id": player_id,
        "player_name": person.get("fullName"),
        "team": team,
        "role": "SP" if is_start else "RP",
        "is_start": is_start,
        "innings_pitched": innings,
        "hits": _stat(pitching, "hits"),
        "home_runs": _stat(pitching, "homeRuns"),
        "walks": _stat(pitching, "baseOnBalls"),
        "hit_by_pitch": _stat(pitching, "hitBatsmen"),
        "strikeouts": _stat(pitching, "strikeOuts"),
        "batters_faced": _stat(pitching, "battersFaced"),
        "pitches": _stat(pitching, "numberOfPitches", _stat(pitching, "pitchesThrown")),
        "is_closer": int(saves > 0 or save_opportunities > 0 or games_finished > 0),
        "is_high_leverage": int(saves > 0 or holds > 0 or blown_saves > 0 or save_opportunities > 0),
    }


def _load_people_metadata(people_csv: str | Path | None) -> pd.DataFrame:
    if people_csv is None:
        return pd.DataFrame(columns=["player_id", "bats", "throws"])
    people = read_csv_table(people_csv)
    people["player_id"] = pd.to_numeric(people["player_id"], errors="coerce")
    return people.dropna(subset=["player_id"]).drop_duplicates("player_id", keep="last")


def _metadata_lookup(people: pd.DataFrame, column: str) -> dict[int, object]:
    if people.empty or column not in people.columns:
        return {}
    return {
        int(row["player_id"]): row[column]
        for _, row in people[["player_id", column]].dropna().iterrows()
    }


def _lookup_player_metadata(lookup: dict[int, object], player_id: object) -> object:
    if pd.isna(player_id):
        return np.nan
    try:
        return lookup.get(int(float(player_id)), np.nan)
    except (TypeError, ValueError):
        return np.nan


def standardize_mlb_stats_api_boxscores(
    *,
    schedule_csv: str | Path,
    boxscore_dir: str | Path,
    output_dir: str | Path,
    prediction_mode: str = "confirmed_lineup",
    people_csv: str | Path | None = None,
) -> dict[str, Path]:
    """Create project-standard raw tables from MLB Stats API schedule and boxscores."""

    schedule = read_csv_table(schedule_csv)
    schedule["game_id"] = schedule["game_id"].astype(str)
    schedule = schedule.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    boxscore_paths = { _boxscore_game_id(path): path for path in Path(boxscore_dir).glob("*_boxscore.json") }
    people = _load_people_metadata(people_csv)
    bats_by_player = _metadata_lookup(people, "bats")
    throws_by_player = _metadata_lookup(people, "throws")

    games_rows: list[dict[str, object]] = []
    lineup_rows: list[dict[str, object]] = []
    batting_rows: list[dict[str, object]] = []
    pitching_rows: list[dict[str, object]] = []
    weather_rows: list[dict[str, object]] = []

    for _, game in schedule.iterrows():
        game_id = str(game["game_id"])
        boxscore_path = boxscore_paths.get(game_id)
        if boxscore_path is None:
            continue
        boxscore = json.loads(boxscore_path.read_text(encoding="utf-8"))
        season = int(game["season"])
        game_date = game["game_date"]
        home_team = game.get("home_team_abbrev") or game.get("home_team")
        away_team = game.get("away_team_abbrev") or game.get("away_team")

        games_rows.append(
            {
                "game_id": game_id,
                "game_date": game_date,
                "season": season,
                "home_team": home_team,
                "away_team": away_team,
                "home_sp_id": game.get("home_sp_id"),
                "away_sp_id": game.get("away_sp_id"),
                "home_sp_hand": _lookup_player_metadata(throws_by_player, game.get("home_sp_id")),
                "away_sp_hand": _lookup_player_metadata(throws_by_player, game.get("away_sp_id")),
                "home_score": game.get("home_score"),
                "away_score": game.get("away_score"),
                "venue_id": game.get("venue_id"),
                "venue_name": game.get("venue_name"),
                "source": "mlb_stats_api",
            }
        )

        weather_rows.append({"game_id": game_id, **_parse_weather(_info_map(boxscore))})

        for side, team_code, opposing_starter_id in [
            ("home", home_team, game.get("away_sp_id")),
            ("away", away_team, game.get("home_sp_id")),
        ]:
            team = boxscore.get("teams", {}).get(side, {})
            players = team.get("players", {})
            starter_ids = set()
            probable_id = game.get(f"{side}_sp_id")
            if pd.notna(probable_id):
                starter_ids.add(int(probable_id))
            opposing_pitcher_hand = np.nan
            if pd.notna(opposing_starter_id):
                opposing_pitcher_hand = throws_by_player.get(int(opposing_starter_id), np.nan)

            for order_index, player_id in enumerate(team.get("battingOrder", []) or [], start=1):
                player = players.get(_player_key(player_id), {})
                lineup_rows.append(
                    {
                        "game_id": game_id,
                        "team": team_code,
                        "player_id": player_id,
                        "player_name": player.get("person", {}).get("fullName"),
                        "batting_order": order_index,
                        "bats": bats_by_player.get(int(player_id), np.nan),
                        "prediction_mode": prediction_mode,
                    }
                )

            for player in players.values():
                batting_row = _normalize_batting_row(
                    game_id=game_id,
                    game_date=game_date,
                    season=season,
                    team=team_code,
                    player=player,
                    opposing_pitcher_hand=opposing_pitcher_hand,
                )
                if batting_row is not None:
                    batting_rows.append(batting_row)

                pitching_row = _normalize_pitching_row(
                    game_id=game_id,
                    game_date=game_date,
                    season=season,
                    team=team_code,
                    player=player,
                    starter_ids=starter_ids,
                )
                if pitching_row is not None:
                    pitching_rows.append(pitching_row)

    outputs = {
        "games": output / "games.csv",
        "lineups": output / "lineups.csv",
        "batting_logs": output / "batting_logs.csv",
        "pitcher_logs": output / "pitcher_logs.csv",
        "weather": output / "weather.csv",
    }
    write_csv_table(pd.DataFrame(games_rows), outputs["games"])
    write_csv_table(pd.DataFrame(lineup_rows), outputs["lineups"])
    write_csv_table(pd.DataFrame(batting_rows), outputs["batting_logs"])
    write_csv_table(pd.DataFrame(pitching_rows), outputs["pitcher_logs"])
    write_csv_table(pd.DataFrame(weather_rows), outputs["weather"])
    return outputs
