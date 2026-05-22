"""Rebuild the Statcast-enriched feature and report pipeline.

Default behavior reuses existing season-level Statcast CSVs. Pass --collect to
refresh Baseball Savant / Statcast raw data first.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.features import FeatureBuildConfig, FeatureBuilder
from mlb_winprob.reporting import read_feature_tables, write_feature_quality_report, write_season_holdout_report
from mlb_winprob.statcast import aggregate_statcast_batting, aggregate_statcast_pitching, merge_statcast_quality


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", default="2021,2022,2023,2024,2025")
    parser.add_argument("--standardized-root", default="data/standardized")
    parser.add_argument("--raw-statcast-root", default="data/raw/statcast")
    parser.add_argument("--processed-root", default="data/processed")
    parser.add_argument("--outputs-root", default="outputs")
    parser.add_argument("--park-factors", default="data/processed/park_factors_empirical_previous_season_2022_2026.csv")
    parser.add_argument("--venues", default="data/raw/mlb_stats_api/venues_2021_2025.csv")
    parser.add_argument("--dataset-name", default="features_confirmed_2021_2025_with_park_factors_statcast")
    parser.add_argument("--models", default="elo,logistic,random_forest")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--chunk-days", type=int, default=7)
    parser.add_argument("--force-collect", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def output_paths(args: argparse.Namespace, seasons: list[int]) -> dict[str, object]:
    raw_root = Path(args.raw_statcast_root)
    standardized_root = Path(args.standardized_root)
    processed_root = Path(args.processed_root)
    outputs_root = Path(args.outputs_root)
    season_label = f"{min(seasons)}_{max(seasons)}" if seasons == list(range(min(seasons), max(seasons) + 1)) else "_".join(map(str, seasons))
    return {
        "statcast_raw": {season: raw_root / f"statcast_{season}.csv" for season in seasons},
        "statcast_quality": {season: standardized_root / f"statcast_{season}" for season in seasons},
        "standardized": {season: standardized_root / f"mlb_stats_api_{season}" for season in seasons},
        "season_features": {
            season: processed_root / f"features_confirmed_{season}_with_park_factors_statcast.csv" for season in seasons
        },
        "combined_features": processed_root / f"{args.dataset_name}.csv",
        "quality_output": outputs_root / "quality" / args.dataset_name,
        "holdout_output": outputs_root / "experiments" / f"season_holdout_confirmed_{season_label}_with_park_factors_statcast",
    }


def print_plan(args: argparse.Namespace, seasons: list[int]) -> None:
    paths = output_paths(args, seasons)
    print("Statcast feature pipeline plan")
    print(f"seasons: {', '.join(map(str, seasons))}")
    print(f"collect raw Statcast: {args.collect}")
    print(f"combined features: {paths['combined_features']}")
    print(f"quality report: {paths['quality_output']}")
    print(f"holdout report: {paths['holdout_output']}")


def run_collect(args: argparse.Namespace, seasons: list[int]) -> None:
    command = [
        sys.executable,
        str(Path(__file__).with_name("collect_statcast_parallel.py")),
        "--seasons",
        ",".join(map(str, seasons)),
        "--standardized-root",
        args.standardized_root,
        "--output-root",
        args.raw_statcast_root,
        "--workers",
        str(args.workers),
        "--chunk-days",
        str(args.chunk_days),
    ]
    if args.force_collect:
        command.append("--force")
    subprocess.run(command, check=True)


def aggregate_statcast(season: int, raw_path: Path, output_dir: Path) -> tuple[Path, Path]:
    batting_output = output_dir / "batting_quality.csv"
    pitching_output = output_dir / "pitching_quality.csv"
    events = read_csv_table(raw_path)
    batting = aggregate_statcast_batting(events)
    pitching = aggregate_statcast_pitching(events)
    write_csv_table(batting, batting_output)
    write_csv_table(pitching, pitching_output)
    print(f"{season}: wrote Statcast quality rows batting={len(batting)} pitching={len(pitching)}")
    return batting_output, pitching_output


def merge_logs(season: int, standardized_dir: Path, batting_quality: Path, pitching_quality: Path) -> tuple[Path, Path]:
    batting_output = standardized_dir / "batting_logs_statcast.csv"
    pitching_output = standardized_dir / "pitcher_logs_statcast.csv"
    batting, pitching = merge_statcast_quality(
        batting_logs=read_csv_table(standardized_dir / "batting_logs.csv"),
        pitcher_logs=read_csv_table(standardized_dir / "pitcher_logs.csv"),
        statcast_batting=read_csv_table(batting_quality),
        statcast_pitching=read_csv_table(pitching_quality),
    )
    write_csv_table(batting, batting_output)
    write_csv_table(pitching, pitching_output)
    print(f"{season}: wrote enriched logs batting={len(batting)} pitching={len(pitching)}")
    return batting_output, pitching_output


def build_features(
    season: int,
    standardized_dir: Path,
    batting_logs: Path,
    pitcher_logs: Path,
    park_factors: Path,
    venues: Path | None,
    output: Path,
    prediction_mode: str,
) -> Path:
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode=prediction_mode))
    features = builder.build(
        games=read_csv_table(standardized_dir / "games.csv"),
        batting_logs=read_csv_table(batting_logs),
        pitcher_logs=read_csv_table(pitcher_logs),
        lineups=read_csv_table(standardized_dir / "lineups.csv"),
        weather=read_csv_table(standardized_dir / "weather.csv"),
        park_factors=read_csv_table(park_factors),
        venues=read_csv_table(venues) if venues is not None and venues.exists() else None,
    )
    write_csv_table(features, output)
    print(f"{season}: wrote feature rows={len(features)} columns={features.shape[1]}")
    return output


def main() -> None:
    args = parse_args()
    seasons = parse_csv_ints(args.seasons)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    model_names = parse_csv_strings(args.models)
    paths = output_paths(args, seasons)
    print_plan(args, seasons)
    if args.dry_run:
        return

    if args.collect:
        run_collect(args, seasons)

    raw_paths: dict[int, Path] = paths["statcast_raw"]  # type: ignore[assignment]
    quality_dirs: dict[int, Path] = paths["statcast_quality"]  # type: ignore[assignment]
    standardized_dirs: dict[int, Path] = paths["standardized"]  # type: ignore[assignment]
    season_feature_paths: dict[int, Path] = paths["season_features"]  # type: ignore[assignment]
    feature_outputs: list[Path] = []
    for season in seasons:
        raw_path = raw_paths[season]
        if not raw_path.exists():
            raise FileNotFoundError(f"Missing Statcast raw CSV for {season}: {raw_path}")
        batting_quality, pitching_quality = aggregate_statcast(season, raw_path, quality_dirs[season])
        batting_logs, pitcher_logs = merge_logs(season, standardized_dirs[season], batting_quality, pitching_quality)
        feature_outputs.append(
            build_features(
                season,
                standardized_dirs[season],
                batting_logs,
                pitcher_logs,
                Path(args.park_factors),
                Path(args.venues) if args.venues else None,
                season_feature_paths[season],
                args.prediction_mode,
            )
        )

    combined_features = read_feature_tables(feature_outputs)
    combined_path: Path = paths["combined_features"]  # type: ignore[assignment]
    write_csv_table(combined_features, combined_path)
    print(f"combined: wrote feature rows={len(combined_features)} to {combined_path}")

    quality_output: Path = paths["quality_output"]  # type: ignore[assignment]
    holdout_output: Path = paths["holdout_output"]  # type: ignore[assignment]
    write_feature_quality_report(combined_features, quality_output)
    print(f"quality report: {quality_output}")
    write_season_holdout_report(
        combined_features,
        holdout_output,
        holdout_seasons=holdout_seasons,
        model_names=model_names,
        prediction_mode=args.prediction_mode,
    )
    print(f"holdout report: {holdout_output}")


if __name__ == "__main__":
    main()
