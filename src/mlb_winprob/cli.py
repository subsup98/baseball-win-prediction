"""Command line entrypoints."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from time import sleep

import joblib
import pandas as pd

from mlb_winprob.data_sources import (
    ChadwickRegisterCollector,
    LahmanCollector,
    MLBStatsApiCollector,
    OpenMeteoArchiveCollector,
    PyBaseballCollector,
    RetrosheetCollector,
    default_collection_workers,
    download_url,
    read_csv_table,
    write_csv_table,
)
from mlb_winprob.experiments import run_model_experiments, select_feature_columns
from mlb_winprob.features import FeatureBuilder
from mlb_winprob.park_factors import build_empirical_park_factors
from mlb_winprob.prediction import build_prediction_result, simple_key_reasons
from mlb_winprob.reporting import read_feature_tables, write_feature_quality_report, write_season_holdout_report
from mlb_winprob.schemas import FeatureBuildConfig
from mlb_winprob.standardize import standardize_mlb_stats_api_boxscores
from mlb_winprob.statcast import aggregate_statcast_batting, aggregate_statcast_pitching, merge_statcast_quality
from mlb_winprob.weather import augment_weather_with_open_meteo


def _add_common_raw_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--games", required=True)
    parser.add_argument("--batting-logs", required=True)
    parser.add_argument("--pitcher-logs", required=True)
    parser.add_argument("--lineups", required=True)
    parser.add_argument("--weather")
    parser.add_argument("--park-factors")


def build_features_command(args: argparse.Namespace) -> None:
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode=args.prediction_mode))
    features = builder.build(
        games=read_csv_table(args.games),
        batting_logs=read_csv_table(args.batting_logs),
        pitcher_logs=read_csv_table(args.pitcher_logs),
        lineups=read_csv_table(args.lineups),
        weather=read_csv_table(args.weather) if args.weather else None,
        park_factors=read_csv_table(args.park_factors) if args.park_factors else None,
    )
    write_csv_table(features, args.output)
    print(f"Wrote {len(features)} feature rows to {args.output}")


def combine_features_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.inputs)
    write_csv_table(features, args.output)
    print(f"Wrote {len(features)} combined feature rows to {args.output}")


def feature_quality_report_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.features)
    paths = write_feature_quality_report(features, args.output_dir)
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def season_holdout_report_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.features)
    model_names = [value.strip() for value in args.models.split(",") if value.strip()]
    holdout_seasons = [int(value.strip()) for value in args.holdout_seasons.split(",") if value.strip()]
    paths = write_season_holdout_report(
        features,
        args.output_dir,
        holdout_seasons=holdout_seasons,
        model_names=model_names,
        prediction_mode=args.prediction_mode,
    )
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def build_empirical_park_factors_command(args: argparse.Namespace) -> None:
    park_factors = build_empirical_park_factors(
        args.standardized_dirs,
        lag_seasons=args.lag_seasons,
        min_games=args.min_games,
    )
    write_csv_table(park_factors, args.output)
    print(f"Wrote {len(park_factors)} empirical park factor rows to {args.output}")


def train_command(args: argparse.Namespace) -> None:
    features = read_csv_table(args.features)
    model_names = args.models.split(",") if args.models else None
    result = run_model_experiments(
        features,
        model_names=model_names,
        holdout_season=args.holdout_season,
        prediction_mode=args.prediction_mode,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result.metrics.to_csv(output_dir / "metrics.csv", index=False)
    for model_name, table in result.calibration.items():
        table.to_csv(output_dir / f"calibration_{model_name}.csv", index=False)
    if result.fitted_models:
        best_name = result.best_model_name
        joblib.dump(
            {
                "model_name": best_name,
                "feature_columns": result.feature_columns,
                "estimator": result.fitted_models[best_name],
            },
            output_dir / "best_model.joblib",
        )
        print(result.metrics.to_string(index=False))
        print(f"Best model: {best_name}")
    else:
        print("No models were trained. Optional booster dependencies may be missing.")


def predict_command(args: argparse.Namespace) -> None:
    bundle = joblib.load(args.model)
    features = read_csv_table(args.features)
    feature_columns = bundle["feature_columns"]
    estimator = bundle["estimator"]
    probabilities = estimator.predict_proba(features[feature_columns])[:, 1]
    for (_, row), probability in zip(features.iterrows(), probabilities, strict=False):
        result = build_prediction_result(
            float(probability),
            model_name=args.model_name or bundle.get("model_name", "unknown"),
            prediction_mode=args.prediction_mode,
            key_reasons=simple_key_reasons(row),
        )
        print(json.dumps(result.as_dict(), ensure_ascii=False))


def collect_statcast_command(args: argparse.Namespace) -> None:
    collector = PyBaseballCollector()
    frame = collector.statcast(args.start_date, args.end_date)
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} Statcast rows to {args.output}")


def aggregate_statcast_command(args: argparse.Namespace) -> None:
    events = read_csv_table(args.statcast)
    batting = aggregate_statcast_batting(events)
    pitching = aggregate_statcast_pitching(events)
    write_csv_table(batting, args.batting_output)
    write_csv_table(pitching, args.pitching_output)
    print(f"Wrote {len(batting)} Statcast batting quality rows to {args.batting_output}")
    print(f"Wrote {len(pitching)} Statcast pitching quality rows to {args.pitching_output}")


def merge_statcast_logs_command(args: argparse.Namespace) -> None:
    batting, pitching = merge_statcast_quality(
        batting_logs=read_csv_table(args.batting_logs),
        pitcher_logs=read_csv_table(args.pitcher_logs),
        statcast_batting=read_csv_table(args.statcast_batting),
        statcast_pitching=read_csv_table(args.statcast_pitching),
    )
    write_csv_table(batting, args.batting_output)
    write_csv_table(pitching, args.pitching_output)
    print(f"Wrote {len(batting)} enriched batting log rows to {args.batting_output}")
    print(f"Wrote {len(pitching)} enriched pitcher log rows to {args.pitching_output}")


def collect_fangraphs_command(args: argparse.Namespace) -> None:
    collector = PyBaseballCollector()
    if args.table == "batting":
        frame = collector.batting_stats(args.season)
    else:
        frame = collector.pitching_stats(args.season)
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} FanGraphs {args.table} rows to {args.output}")


def collect_mlb_schedule_command(args: argparse.Namespace) -> None:
    collector = MLBStatsApiCollector()
    frame = collector.schedule(
        args.start_date,
        args.end_date,
        sport_id=args.sport_id,
        hydrate=args.hydrate,
    )
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} MLB Stats API schedule rows to {args.output}")


def _collection_progress(label: str):
    last_reported = 0

    def progress(downloaded: int, skipped: int, failed: int, total: int) -> None:
        nonlocal last_reported
        completed = downloaded + skipped + failed
        should_report = completed == total or completed - last_reported >= 50
        if should_report:
            last_reported = completed
            print(
                f"{label}: {completed}/{total} "
                f"(downloaded={downloaded}, skipped={skipped}, failed={failed})",
                flush=True,
            )

    return progress


def collect_mlb_boxscores_command(args: argparse.Namespace) -> None:
    schedule = read_csv_table(args.games)
    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    if args.limit:
        game_ids = game_ids[: args.limit]
    workers = args.workers or default_collection_workers()
    print(f"Collecting {len(game_ids)} MLB Stats API boxscores with {workers} workers", flush=True)
    paths = MLBStatsApiCollector().save_boxscores(
        game_ids,
        args.output_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Boxscores"),
    )
    print(f"Wrote {len(paths)} MLB Stats API boxscore JSON files to {args.output_dir}")


def collect_mlb_feeds_command(args: argparse.Namespace) -> None:
    schedule = read_csv_table(args.games)
    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    if args.limit:
        game_ids = game_ids[: args.limit]
    workers = args.workers or default_collection_workers()
    print(f"Collecting {len(game_ids)} MLB Stats API feeds with {workers} workers", flush=True)
    paths = MLBStatsApiCollector().save_game_feeds(
        game_ids,
        args.output_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Feeds"),
    )
    print(f"Wrote {len(paths)} MLB Stats API live feed JSON files to {args.output_dir}")


def collect_mlb_people_command(args: argparse.Namespace) -> None:
    player_ids: set[int] = set()
    for path in args.inputs:
        frame = read_csv_table(path)
        for column in args.id_columns.split(","):
            if column in frame.columns:
                values = pd.to_numeric(frame[column], errors="coerce").dropna().astype(int)
                player_ids.update(values.tolist())
    people = MLBStatsApiCollector().people(sorted(player_ids))
    write_csv_table(people, args.output)
    print(f"Wrote {len(people)} MLB Stats API people rows to {args.output}")


def collect_mlb_venues_command(args: argparse.Namespace) -> None:
    venue_ids: set[int] = set()
    for path in args.inputs:
        frame = read_csv_table(path)
        if "venue_id" not in frame.columns:
            continue
        values = pd.to_numeric(frame["venue_id"], errors="coerce").dropna().astype(int)
        venue_ids.update(values.tolist())
    venues = MLBStatsApiCollector().venues(sorted(venue_ids))
    write_csv_table(venues, args.output)
    print(f"Wrote {len(venues)} MLB Stats API venue rows to {args.output}")


def augment_weather_openmeteo_command(args: argparse.Namespace) -> None:
    augmented = augment_weather_with_open_meteo(
        games=read_csv_table(args.games),
        weather=read_csv_table(args.weather),
        venues=read_csv_table(args.venues),
        collector=OpenMeteoArchiveCollector(),
    )
    write_csv_table(augmented, args.output)
    filled = pd.to_numeric(augmented.get("humidity"), errors="coerce").notna().sum()
    print(f"Wrote {len(augmented)} weather rows to {args.output} (humidity_non_null={filled})")


def collect_retrosheet_command(args: argparse.Namespace) -> None:
    path = RetrosheetCollector().download(args.dataset, args.output)
    print(f"Wrote Retrosheet {args.dataset} to {path}")


def collect_lahman_command(args: argparse.Namespace) -> None:
    collector = LahmanCollector()
    if args.archive:
        path = collector.download_archive(args.output)
    else:
        path = collector.download_table(args.table, args.output)
    print(f"Wrote Lahman data to {path}")


def collect_chadwick_people_command(args: argparse.Namespace) -> None:
    path = ChadwickRegisterCollector().download_people(args.output)
    print(f"Wrote Chadwick register people.csv to {path}")


def download_url_command(args: argparse.Namespace) -> None:
    path = download_url(args.url, args.output)
    print(f"Wrote {args.url} to {path}")


def standardize_mlb_boxscores_command(args: argparse.Namespace) -> None:
    outputs = standardize_mlb_stats_api_boxscores(
        schedule_csv=args.schedule,
        boxscore_dir=args.boxscore_dir,
        output_dir=args.output_dir,
        prediction_mode=args.prediction_mode,
        people_csv=args.people,
    )
    for name, path in outputs.items():
        print(f"Wrote {name}: {path}")


def collect_mlb_season_dataset_command(args: argparse.Namespace) -> None:
    collector = MLBStatsApiCollector()
    root = Path(args.output_root)
    raw_root = root / "raw" / "mlb_stats_api"
    standardized_root = root / "standardized"
    processed_root = root / "processed"
    raw_root.mkdir(parents=True, exist_ok=True)
    standardized_root.mkdir(parents=True, exist_ok=True)
    processed_root.mkdir(parents=True, exist_ok=True)

    for season in range(args.start_season, args.end_season + 1):
        season_label = str(season)
        print(f"=== Season {season_label} ===", flush=True)
        schedule_path = raw_root / f"schedule_{season_label}.csv"
        boxscore_dir = raw_root / f"boxscores_{season_label}"
        people_path = raw_root / f"people_{season_label}.csv"
        standardized_dir = standardized_root / f"mlb_stats_api_{season_label}"
        feature_path = processed_root / f"features_confirmed_{season_label}.csv"

        if schedule_path.exists() and not args.refresh_schedule:
            schedule = read_csv_table(schedule_path)
            print(f"Using existing schedule: {schedule_path} ({len(schedule)} rows)", flush=True)
        else:
            schedule = collector.schedule(f"{season}-01-01", f"{season}-12-31")
            if args.game_types:
                allowed = {value.strip() for value in args.game_types.split(",") if value.strip()}
                schedule = schedule[schedule["game_type"].isin(allowed)].copy()
            schedule = schedule.dropna(subset=["home_score", "away_score"])
            schedule = schedule.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last")
            write_csv_table(schedule, schedule_path)
            print(f"Wrote schedule: {schedule_path} ({len(schedule)} rows)", flush=True)

        if args.schedule_only:
            continue

        game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
        if args.limit:
            game_ids = game_ids[: args.limit]
        before_existing = len(list(boxscore_dir.glob("*_boxscore.json"))) if boxscore_dir.exists() else 0
        workers = args.workers or default_collection_workers()
        print(f"Collecting {len(game_ids)} boxscores with {workers} workers", flush=True)
        paths = collector.save_boxscores(
            game_ids,
            boxscore_dir,
            skip_existing=True,
            workers=workers,
            progress_callback=_collection_progress(f"Boxscores {season_label}"),
        )
        after_existing = len(list(boxscore_dir.glob("*_boxscore.json")))
        print(
            f"Boxscores ready: {after_existing}/{len(game_ids)} files "
            f"(previously {before_existing})",
            flush=True,
        )
        if args.pause_seconds:
            sleep(args.pause_seconds)

        initial_outputs = standardize_mlb_stats_api_boxscores(
            schedule_csv=schedule_path,
            boxscore_dir=boxscore_dir,
            output_dir=standardized_dir,
            prediction_mode="confirmed_lineup",
        )
        people_inputs = [
            initial_outputs["games"],
            initial_outputs["lineups"],
            initial_outputs["pitcher_logs"],
            initial_outputs["batting_logs"],
        ]
        player_ids: set[int] = set()
        for path in people_inputs:
            frame = read_csv_table(path)
            for column in ["player_id", "home_sp_id", "away_sp_id"]:
                if column in frame.columns:
                    values = pd.to_numeric(frame[column], errors="coerce").dropna().astype(int)
                    player_ids.update(values.tolist())
        if people_path.exists() and not args.refresh_people:
            people = read_csv_table(people_path)
            print(f"Using existing people metadata: {people_path} ({len(people)} rows)", flush=True)
        else:
            people = collector.people(sorted(player_ids))
            write_csv_table(people, people_path)
            print(f"Wrote people metadata: {people_path} ({len(people)} rows)", flush=True)

        standardize_mlb_stats_api_boxscores(
            schedule_csv=schedule_path,
            boxscore_dir=boxscore_dir,
            output_dir=standardized_dir,
            prediction_mode="confirmed_lineup",
            people_csv=people_path,
        )
        builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
        features = builder.build(
            games=read_csv_table(standardized_dir / "games.csv"),
            batting_logs=read_csv_table(standardized_dir / "batting_logs.csv"),
            pitcher_logs=read_csv_table(standardized_dir / "pitcher_logs.csv"),
            lineups=read_csv_table(standardized_dir / "lineups.csv"),
            weather=read_csv_table(standardized_dir / "weather.csv"),
        )
        write_csv_table(features, feature_path)
        print(f"Wrote features: {feature_path} ({features.shape[0]} rows x {features.shape[1]} columns)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="mlb-winprob")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build-features")
    _add_common_raw_args(build_parser)
    build_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    build_parser.add_argument("--output", required=True)
    build_parser.set_defaults(func=build_features_command)

    combine_parser = subparsers.add_parser("combine-features")
    combine_parser.add_argument("--inputs", nargs="+", required=True)
    combine_parser.add_argument("--output", required=True)
    combine_parser.set_defaults(func=combine_features_command)

    quality_parser = subparsers.add_parser("feature-quality-report")
    quality_parser.add_argument("--features", nargs="+", required=True)
    quality_parser.add_argument("--output-dir", required=True)
    quality_parser.set_defaults(func=feature_quality_report_command)

    holdout_parser = subparsers.add_parser("season-holdout-report")
    holdout_parser.add_argument("--features", nargs="+", required=True)
    holdout_parser.add_argument("--output-dir", required=True)
    holdout_parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    holdout_parser.add_argument("--models", default="elo,logistic,random_forest")
    holdout_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    holdout_parser.set_defaults(func=season_holdout_report_command)

    park_parser = subparsers.add_parser("build-empirical-park-factors")
    park_parser.add_argument("--standardized-dirs", nargs="+", required=True)
    park_parser.add_argument("--output", required=True)
    park_parser.add_argument("--lag-seasons", type=int, default=1)
    park_parser.add_argument("--min-games", type=int, default=20)
    park_parser.set_defaults(func=build_empirical_park_factors_command)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--features", required=True)
    train_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"])
    train_parser.add_argument("--holdout-season", type=int)
    train_parser.add_argument("--models", help="Comma-separated model names. Defaults to all available models.")
    train_parser.add_argument("--output-dir", required=True)
    train_parser.set_defaults(func=train_command)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--features", required=True)
    predict_parser.add_argument("--model", required=True)
    predict_parser.add_argument("--model-name")
    predict_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    predict_parser.set_defaults(func=predict_command)

    collect_parser = subparsers.add_parser("collect-statcast")
    collect_parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    collect_parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    collect_parser.add_argument("--output", required=True)
    collect_parser.set_defaults(func=collect_statcast_command)

    statcast_aggregate_parser = subparsers.add_parser("aggregate-statcast")
    statcast_aggregate_parser.add_argument("--statcast", required=True)
    statcast_aggregate_parser.add_argument("--batting-output", required=True)
    statcast_aggregate_parser.add_argument("--pitching-output", required=True)
    statcast_aggregate_parser.set_defaults(func=aggregate_statcast_command)

    statcast_merge_parser = subparsers.add_parser("merge-statcast-logs")
    statcast_merge_parser.add_argument("--batting-logs", required=True)
    statcast_merge_parser.add_argument("--pitcher-logs", required=True)
    statcast_merge_parser.add_argument("--statcast-batting", required=True)
    statcast_merge_parser.add_argument("--statcast-pitching", required=True)
    statcast_merge_parser.add_argument("--batting-output", required=True)
    statcast_merge_parser.add_argument("--pitching-output", required=True)
    statcast_merge_parser.set_defaults(func=merge_statcast_logs_command)

    fangraphs_parser = subparsers.add_parser("collect-fangraphs")
    fangraphs_parser.add_argument("--season", type=int, required=True)
    fangraphs_parser.add_argument("--table", choices=["batting", "pitching"], required=True)
    fangraphs_parser.add_argument("--output", required=True)
    fangraphs_parser.set_defaults(func=collect_fangraphs_command)

    schedule_parser = subparsers.add_parser("collect-mlb-schedule")
    schedule_parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    schedule_parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    schedule_parser.add_argument("--sport-id", type=int, default=1)
    schedule_parser.add_argument("--hydrate", default="probablePitcher,venue,team,linescore")
    schedule_parser.add_argument("--output", required=True)
    schedule_parser.set_defaults(func=collect_mlb_schedule_command)

    boxscore_parser = subparsers.add_parser("collect-mlb-boxscores")
    boxscore_parser.add_argument("--games", required=True, help="CSV from collect-mlb-schedule")
    boxscore_parser.add_argument("--output-dir", required=True)
    boxscore_parser.add_argument("--limit", type=int)
    boxscore_parser.add_argument("--workers", type=int, help="Parallel workers. Defaults to min(32, CPU count * 2).")
    boxscore_parser.add_argument("--no-skip-existing", action="store_true")
    boxscore_parser.set_defaults(func=collect_mlb_boxscores_command)

    feed_parser = subparsers.add_parser("collect-mlb-feeds")
    feed_parser.add_argument("--games", required=True, help="CSV from collect-mlb-schedule")
    feed_parser.add_argument("--output-dir", required=True)
    feed_parser.add_argument("--limit", type=int)
    feed_parser.add_argument("--workers", type=int, help="Parallel workers. Defaults to min(32, CPU count * 2).")
    feed_parser.add_argument("--no-skip-existing", action="store_true")
    feed_parser.set_defaults(func=collect_mlb_feeds_command)

    people_parser = subparsers.add_parser("collect-mlb-people")
    people_parser.add_argument("--inputs", nargs="+", required=True, help="CSV files containing MLBAM player id columns")
    people_parser.add_argument(
        "--id-columns",
        default="player_id,home_sp_id,away_sp_id",
        help="Comma-separated columns to scan for MLBAM player ids",
    )
    people_parser.add_argument("--output", required=True)
    people_parser.set_defaults(func=collect_mlb_people_command)

    venues_parser = subparsers.add_parser("collect-mlb-venues")
    venues_parser.add_argument("--inputs", nargs="+", required=True, help="CSV files containing venue_id columns")
    venues_parser.add_argument("--output", required=True)
    venues_parser.set_defaults(func=collect_mlb_venues_command)

    openmeteo_parser = subparsers.add_parser("augment-weather-openmeteo")
    openmeteo_parser.add_argument("--games", required=True)
    openmeteo_parser.add_argument("--weather", required=True)
    openmeteo_parser.add_argument("--venues", required=True)
    openmeteo_parser.add_argument("--output", required=True)
    openmeteo_parser.set_defaults(func=augment_weather_openmeteo_command)

    retrosheet_parser = subparsers.add_parser("collect-retrosheet")
    retrosheet_parser.add_argument(
        "--dataset",
        choices=sorted(RetrosheetCollector.downloads),
        required=True,
    )
    retrosheet_parser.add_argument("--output", required=True)
    retrosheet_parser.set_defaults(func=collect_retrosheet_command)

    lahman_parser = subparsers.add_parser("collect-lahman")
    lahman_parser.add_argument("--table", default="People")
    lahman_parser.add_argument("--archive", action="store_true")
    lahman_parser.add_argument("--output", required=True)
    lahman_parser.set_defaults(func=collect_lahman_command)

    chadwick_parser = subparsers.add_parser("collect-chadwick-people")
    chadwick_parser.add_argument("--output", required=True)
    chadwick_parser.set_defaults(func=collect_chadwick_people_command)

    url_parser = subparsers.add_parser("download-url")
    url_parser.add_argument("--url", required=True)
    url_parser.add_argument("--output", required=True)
    url_parser.set_defaults(func=download_url_command)

    standardize_parser = subparsers.add_parser("standardize-mlb-boxscores")
    standardize_parser.add_argument("--schedule", required=True)
    standardize_parser.add_argument("--boxscore-dir", required=True)
    standardize_parser.add_argument("--output-dir", required=True)
    standardize_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    standardize_parser.add_argument("--people", help="Optional MLB Stats API people metadata CSV")
    standardize_parser.set_defaults(func=standardize_mlb_boxscores_command)

    season_dataset_parser = subparsers.add_parser("collect-mlb-season-dataset")
    season_dataset_parser.add_argument("--start-season", type=int, required=True)
    season_dataset_parser.add_argument("--end-season", type=int, required=True)
    season_dataset_parser.add_argument("--output-root", default="data")
    season_dataset_parser.add_argument("--game-types", default="R", help="Comma-separated game types, e.g. R or R,F,D,L,W")
    season_dataset_parser.add_argument("--limit", type=int, help="Limit games per season for smoke tests")
    season_dataset_parser.add_argument("--schedule-only", action="store_true")
    season_dataset_parser.add_argument("--refresh-schedule", action="store_true")
    season_dataset_parser.add_argument("--refresh-people", action="store_true")
    season_dataset_parser.add_argument("--pause-seconds", type=float, default=0.0)
    season_dataset_parser.add_argument("--workers", type=int, help="Parallel boxscore workers. Defaults to min(32, CPU count * 2).")
    season_dataset_parser.set_defaults(func=collect_mlb_season_dataset_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
