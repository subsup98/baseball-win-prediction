"""Weather source joins and augmentation helpers."""

from __future__ import annotations

from datetime import timedelta

import pandas as pd

from mlb_winprob.data_sources import OpenMeteoArchiveCollector


def _nearest_utc_hour(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True).dt.round("h")


def augment_weather_with_open_meteo(
    *,
    games: pd.DataFrame,
    weather: pd.DataFrame,
    venues: pd.DataFrame,
    collector: OpenMeteoArchiveCollector | None = None,
) -> pd.DataFrame:
    """Fill game-level weather gaps with Open-Meteo hourly historical data."""

    required_game_columns = {"game_id", "game_date", "season", "venue_id"}
    missing_game_columns = required_game_columns - set(games.columns)
    if missing_game_columns:
        raise ValueError(f"games is missing required columns: {sorted(missing_game_columns)}")

    required_venue_columns = {"venue_id", "latitude", "longitude"}
    missing_venue_columns = required_venue_columns - set(venues.columns)
    if missing_venue_columns:
        raise ValueError(f"venues is missing required columns: {sorted(missing_venue_columns)}")

    collector = collector or OpenMeteoArchiveCollector()
    games_for_join = games[["game_id", "game_date", "season", "venue_id"]].copy()
    games_for_join["game_id"] = games_for_join["game_id"].astype(str)
    games_for_join["venue_id"] = pd.to_numeric(games_for_join["venue_id"], errors="coerce")
    games_for_join["season"] = pd.to_numeric(games_for_join["season"], errors="coerce")
    games_for_join["weather_hour"] = _nearest_utc_hour(games_for_join["game_date"])

    venues_for_join = venues.copy()
    venues_for_join["venue_id"] = pd.to_numeric(venues_for_join["venue_id"], errors="coerce")
    venues_for_join["latitude"] = pd.to_numeric(venues_for_join["latitude"], errors="coerce")
    venues_for_join["longitude"] = pd.to_numeric(venues_for_join["longitude"], errors="coerce")
    games_for_join = games_for_join.merge(
        venues_for_join[["venue_id", "latitude", "longitude"]],
        on="venue_id",
        how="left",
    )
    if games_for_join[["latitude", "longitude"]].isna().any(axis=None):
        missing = games_for_join.loc[
            games_for_join[["latitude", "longitude"]].isna().any(axis=1),
            "venue_id",
        ].dropna().unique()
        raise ValueError(f"Missing venue coordinates for venue_id values: {sorted(missing.tolist())}")

    hourly_frames: list[pd.DataFrame] = []
    for (venue_id, season), group in games_for_join.groupby(["venue_id", "season"], dropna=True):
        latitude = float(group["latitude"].iloc[0])
        longitude = float(group["longitude"].iloc[0])
        min_hour = group["weather_hour"].min()
        max_hour = group["weather_hour"].max()
        hourly = collector.hourly_weather(
            latitude=latitude,
            longitude=longitude,
            start_date=min_hour.date().isoformat(),
            end_date=(max_hour.date() + timedelta(days=1)).isoformat(),
        )
        hourly["venue_id"] = venue_id
        hourly["season"] = season
        hourly_frames.append(hourly)

    hourly_weather = pd.concat(hourly_frames, ignore_index=True) if hourly_frames else pd.DataFrame()
    augmented = games_for_join.merge(
        hourly_weather,
        on=["venue_id", "season", "weather_hour"],
        how="left",
    )

    output = weather.copy()
    output["game_id"] = output["game_id"].astype(str)
    output = output.merge(
        augmented[
            [
                "game_id",
                "open_meteo_temperature",
                "humidity",
                "open_meteo_wind_speed",
                "open_meteo_wind_direction_degrees",
            ]
        ],
        on="game_id",
        how="left",
        suffixes=("", "_open_meteo"),
    )
    if "humidity" not in output.columns:
        output["humidity"] = pd.NA
    output["humidity"] = pd.to_numeric(output["humidity"], errors="coerce")
    output["humidity"] = output["humidity"].fillna(pd.to_numeric(output.pop("humidity_open_meteo"), errors="coerce"))
    output["humidity_source"] = pd.Series(pd.NA, index=output.index, dtype="object")
    output.loc[output["humidity"].notna(), "humidity_source"] = "open_meteo_archive"
    return output
