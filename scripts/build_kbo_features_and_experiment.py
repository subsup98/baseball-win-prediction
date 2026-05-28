"""KBO league-common feature build + holdout experiment, mirroring the MLB path.

KBO was built to map into the same canonical tables as MLB, so this script runs
the same FeatureBuilder / feature-quality / season-holdout flow on KBO data. It
adapts the MyKBO canonical tables to the MLB FeatureBuilder contract:

- builds a ``games`` table from the MyKBO schedule (final games only) and injects
  ``home_sp_id`` / ``away_sp_id`` derived from the ``is_start`` flag in
  ``pitcher_logs``;
- renames ``mykbo_player_id`` -> ``player_id`` in the batting / pitcher logs so the
  builder's per-player rolling features line up.

The current version can optionally attach KBO venue metadata, an offline dome
weather stub, and leakage-safe empirical park factors. Real outdoor weather
observations still require a later historical weather backfill.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.features import FeatureBuildConfig, FeatureBuilder
from mlb_winprob.kbo import build_kbo_weather_stub, enrich_kbo_games_with_venues, kbo_venue_seed, write_kbo_venue_seed
from mlb_winprob.park_factors import build_empirical_park_factors
from mlb_winprob.reporting import write_feature_quality_report, write_season_holdout_report


def build_games(schedule: pd.DataFrame, pitcher_logs: pd.DataFrame) -> pd.DataFrame:
    """Final-games schedule plus home/away starting pitcher ids."""

    games = schedule[schedule["is_final"] == 1].copy()
    games = games.dropna(subset=["home_team", "away_team", "home_score", "away_score"])
    keep_columns = ["game_id", "game_date", "season", "home_team", "away_team", "home_score", "away_score", "home_team_win"]
    for optional_column in ["venue_id", "venue_name"]:
        if optional_column in games.columns:
            keep_columns.append(optional_column)
    games = games[keep_columns].copy()
    # Guard against rare duplicate schedule rows (e.g. suspended/resumed games).
    games = games.drop_duplicates("game_id", keep="first")

    starters = pitcher_logs[pitcher_logs["is_start"] == 1][["game_id", "team", "player_id"]].copy()
    # Keep one starter per (game, team) in case of opener edge cases.
    starters = starters.drop_duplicates(["game_id", "team"], keep="first")

    home_sp = starters.rename(columns={"team": "home_team", "player_id": "home_sp_id"})
    away_sp = starters.rename(columns={"team": "away_team", "player_id": "away_sp_id"})
    games = games.merge(home_sp, on=["game_id", "home_team"], how="left")
    games = games.merge(away_sp, on=["game_id", "away_team"], how="left")
    # Final safety: never emit more than one row per game.
    games = games.drop_duplicates("game_id", keep="first")
    return games


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--canonical-dir", default="data/standardized/kbo/canonical_2021_2026")
    parser.add_argument("--schedule", default="data/standardized/kbo/games_mykbo_schedule_2021_2026.csv")
    parser.add_argument("--processed-root", default="data/processed/kbo")
    parser.add_argument("--dataset-name", default="features_confirmed_kbo_2021_2026")
    parser.add_argument("--quality-output", default="outputs/quality/kbo/features_confirmed_kbo_2021_2026")
    parser.add_argument("--holdout-output", default="outputs/experiments/kbo/season_holdout_kbo_2021_2026")
    parser.add_argument("--holdout-seasons", default="2024,2025,2026")
    parser.add_argument("--models", default="elo,logistic,random_forest,random_forest_shallow,extra_trees")
    parser.add_argument("--venues", default="data/standardized/kbo/venues_seed.csv")
    parser.add_argument("--park-factors", default="data/processed/kbo/park_factors_empirical_kbo_2021_2026.csv")
    parser.add_argument("--no-env", action="store_true", help="Skip KBO venue/dome/park-factor inputs and reproduce the league-common baseline.")
    parser.add_argument(
        "--weather",
        default=None,
        help="Optional precomputed KBO weather CSV (e.g. Open-Meteo backfill). When omitted, uses the offline dome-only stub.",
    )
    parser.add_argument("--min-park-games", type=int, default=20)
    parser.add_argument("--skip-holdout", action="store_true")
    args = parser.parse_args()

    canonical = Path(args.canonical_dir)
    schedule = read_csv_table(args.schedule)
    batting_logs = read_csv_table(canonical / "batting_logs.csv").rename(columns={"mykbo_player_id": "player_id"})
    pitcher_logs = read_csv_table(canonical / "pitcher_logs.csv").rename(columns={"mykbo_player_id": "player_id"})
    lineups = read_csv_table(canonical / "lineups.csv")

    for frame in (schedule, batting_logs, pitcher_logs, lineups):
        if "game_id" in frame.columns:
            frame["game_id"] = frame["game_id"].astype("string")
    for frame in (batting_logs, pitcher_logs, lineups):
        if "player_id" in frame.columns:
            frame["player_id"] = pd.to_numeric(frame["player_id"], errors="coerce").astype("Int64").astype("string")

    venues = None
    weather = None
    park_factors = None
    if not args.no_env:
        venues_path = Path(args.venues)
        if not venues_path.exists():
            write_kbo_venue_seed(venues_path)
        venues = read_csv_table(venues_path) if venues_path.exists() else kbo_venue_seed()
        schedule = enrich_kbo_games_with_venues(schedule, venues)

    games = build_games(schedule, pitcher_logs)
    games["home_sp_id"] = games["home_sp_id"].astype("string")
    games["away_sp_id"] = games["away_sp_id"].astype("string")
    if not args.no_env:
        games = enrich_kbo_games_with_venues(games, venues)
        if args.weather:
            weather = read_csv_table(args.weather)
            weather["game_id"] = weather["game_id"].astype("string")
            print(f"using precomputed weather from {args.weather}: {len(weather)} rows")
        else:
            weather = build_kbo_weather_stub(games, venues)
        canonical_games_path = canonical / "games.csv"
        write_csv_table(games, canonical_games_path)
        park_factors_path = Path(args.park_factors)
        park_factors_path.parent.mkdir(parents=True, exist_ok=True)
        write_csv_table(
            build_empirical_park_factors([canonical], min_games=args.min_park_games),
            park_factors_path,
        )
        park_factors = read_csv_table(park_factors_path)
    print(f"games: {len(games)} rows, seasons {sorted(games['season'].dropna().unique())}")
    print(f"home_sp_id null-rate: {games['home_sp_id'].isna().mean():.3f}  away_sp_id null-rate: {games['away_sp_id'].isna().mean():.3f}")
    if "venue_id" in games.columns:
        print(f"venue_id null-rate: {games['venue_id'].isna().mean():.3f}")

    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
        venues=venues,
    )
    # A rare duplicate schedule game can fan out inside the builder's merges;
    # keep exactly one feature row per game.
    before = len(features)
    features = features.drop_duplicates("game_id", keep="first").reset_index(drop=True)
    if len(features) != before:
        print(f"dropped {before - len(features)} duplicate feature row(s); now {len(features)}")
    print(f"features: {len(features)} rows, {features.shape[1]} columns")

    processed_root = Path(args.processed_root)
    processed_root.mkdir(parents=True, exist_ok=True)
    feature_path = processed_root / f"{args.dataset_name}.csv"
    write_csv_table(features, feature_path)
    print(f"wrote features -> {feature_path}")

    write_feature_quality_report(features, Path(args.quality_output))
    print(f"wrote quality report -> {args.quality_output}")

    if not args.skip_holdout:
        write_season_holdout_report(
            features,
            Path(args.holdout_output),
            holdout_seasons=parse_csv_ints(args.holdout_seasons),
            model_names=parse_csv_strings(args.models),
            prediction_mode="confirmed_lineup",
        )
        print(f"wrote holdout report -> {args.holdout_output}")


if __name__ == "__main__":
    main()
