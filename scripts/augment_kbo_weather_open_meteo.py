"""Backfill KBO 2021-2026 outdoor historical weather via Open-Meteo.

Reads canonical KBO games and KBO venue seed (with latitude/longitude/timezone/is_dome),
fetches Open-Meteo hourly observations for each (venue, season) pair, and writes
a weather.csv compatible with the FeatureBuilder weather merge.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.kbo import augment_kbo_weather_with_open_meteo, kbo_venue_seed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", required=True, help="KBO canonical games.csv.")
    parser.add_argument("--venues", default=None, help="KBO venue CSV (defaults to seed).")
    parser.add_argument("--output", required=True, help="Output weather CSV path.")
    args = parser.parse_args()

    games = read_csv_table(args.games)
    venues = read_csv_table(args.venues) if args.venues else kbo_venue_seed()
    print(f"Games: {len(games)} | Venues: {len(venues)} | Seasons: {sorted(games['season'].unique())}")

    weather = augment_kbo_weather_with_open_meteo(games=games, venues=venues)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_csv_table(weather, args.output)

    n = len(weather)
    print(f"\nWrote {n} weather rows to {args.output}")
    for col in ["temperature", "wind_speed", "wind_direction", "humidity"]:
        rate = weather[col].isna().mean()
        print(f"  {col}: null-rate {rate:.4f}")
    print(f"  is_dome counts:")
    print(weather["is_dome"].value_counts(dropna=False).to_string())


if __name__ == "__main__":
    main()
