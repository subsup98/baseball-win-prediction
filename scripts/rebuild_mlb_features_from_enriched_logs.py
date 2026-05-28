"""Rebuild MLB feature tables from already-enriched standardized logs."""

from __future__ import annotations

import argparse
from pathlib import Path

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.features import FeatureBuildConfig, FeatureBuilder
from mlb_winprob.reporting import read_feature_tables, write_feature_quality_report


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", default="2021,2022,2023,2024,2025")
    parser.add_argument("--standardized-root", default="data/standardized")
    parser.add_argument("--processed-root", default="data/processed")
    parser.add_argument("--dataset-name", default="features_confirmed_2021_2025_with_park_factors_statcast_recent_form")
    parser.add_argument("--park-factors", default="data/processed/park_factors_empirical_previous_season_2022_2026.csv")
    parser.add_argument("--venues", default="data/raw/mlb_stats_api/venues_2021_2025.csv")
    parser.add_argument("--quality-output", default="outputs/quality/features_confirmed_2021_2025_with_park_factors_statcast_recent_form")
    args = parser.parse_args()

    seasons = parse_csv_ints(args.seasons)
    processed_root = Path(args.processed_root)
    processed_root.mkdir(parents=True, exist_ok=True)
    feature_paths = []
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
    for season in seasons:
        standardized = Path(args.standardized_root) / f"mlb_stats_api_{season}"
        batting_logs = standardized / "batting_logs_statcast.csv"
        pitcher_logs = standardized / "pitcher_logs_statcast.csv"
        if not batting_logs.exists():
            batting_logs = standardized / "batting_logs.csv"
        if not pitcher_logs.exists():
            pitcher_logs = standardized / "pitcher_logs.csv"
        features = builder.build(
            games=read_csv_table(standardized / "games.csv"),
            batting_logs=read_csv_table(batting_logs),
            pitcher_logs=read_csv_table(pitcher_logs),
            lineups=read_csv_table(standardized / "lineups.csv"),
            weather=read_csv_table(standardized / "weather.csv"),
            park_factors=read_csv_table(args.park_factors),
            venues=read_csv_table(args.venues) if Path(args.venues).exists() else None,
        )
        path = processed_root / f"features_confirmed_{season}_with_park_factors_statcast_recent_form.csv"
        write_csv_table(features, path)
        feature_paths.append(path)
        print(f"{season}: wrote rows={len(features)} columns={features.shape[1]} -> {path}")

    combined = read_feature_tables(feature_paths)
    combined_path = processed_root / f"{args.dataset_name}.csv"
    write_csv_table(combined, combined_path)
    print(f"combined: wrote rows={len(combined)} columns={combined.shape[1]} -> {combined_path}")
    write_feature_quality_report(combined, Path(args.quality_output))
    print(f"quality report -> {args.quality_output}")


if __name__ == "__main__":
    main()
