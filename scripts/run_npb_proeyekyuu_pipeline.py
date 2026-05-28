"""Run the NPB ProEyeKyuu canonical feature pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from mlb_winprob.data_sources import ProEyeKyuuCollector, read_csv_table, write_csv_table
from mlb_winprob.features import FeatureBuilder
from mlb_winprob.npb import (
    standardize_proeyekyuu_game_results,
    standardize_proeyekyuu_game_tables,
    write_npb_feature_set,
    write_npb_model_ready_features,
    write_npb_games_with_venues,
    write_proeyekyuu_batting_detail_audit,
    write_proeyekyuu_coverage_report,
    write_proeyekyuu_games_with_starters,
)
from mlb_winprob.park_factors import build_empirical_park_factors
from mlb_winprob.reporting import write_feature_quality_report
from mlb_winprob.schemas import FeatureBuildConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", default="outputs/npb_smoke")
    parser.add_argument("--venues", default="data/standardized/npb/venues_seed.csv")
    parser.add_argument("--game-limit", type=int, default=10)
    parser.add_argument("--collect-game-pages", action="store_true")
    parser.add_argument("--no-skip-existing", action="store_true")
    parser.add_argument("--min-park-games", type=int, default=1)
    args = parser.parse_args()

    root = Path(args.output_root)
    parsed = root / "standardized" / "npb" / "proeyekyuu"
    games = root / "standardized" / "npb" / "games.csv"
    game_pages = root / "raw" / "proeyekyuu_game_pages"
    game_tables = root / "standardized" / "npb" / "proeyekyuu_game_tables"
    canonical = root / "standardized" / "npb" / f"canonical_{args.game_limit}"
    processed = root / "processed"
    quality = root / "quality" / f"features_confirmed_{args.game_limit}"
    processed.mkdir(parents=True, exist_ok=True)

    if not games.exists():
        standardize_proeyekyuu_game_results(parsed, games)

    if args.collect_game_pages:
        collector = ProEyeKyuuCollector()
        pages = collector.save_game_pages(
            read_csv_table(games),
            game_pages,
            limit=args.game_limit,
            skip_existing=not args.no_skip_existing,
        )
        for page in pages:
            collector.write_html_tables(page, game_tables)

    standardize_proeyekyuu_game_tables(game_tables, games, canonical)
    games_with_starters = root / "standardized" / "npb" / f"games_with_starters_{args.game_limit}.csv"
    write_proeyekyuu_games_with_starters(games, canonical / "pitcher_logs.csv", games_with_starters)
    games_with_venues = root / "standardized" / "npb" / f"games_with_starters_venues_{args.game_limit}.csv"
    write_npb_games_with_venues(games_with_starters, args.venues, games_with_venues)
    write_csv_table(read_csv_table(games_with_venues), canonical / "games.csv")

    park_factors = processed / f"park_factors_empirical_npb_{args.game_limit}.csv"
    write_csv_table(
        build_empirical_park_factors([canonical], min_games=args.min_park_games),
        park_factors,
    )

    features = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup")).build(
        games=read_csv_table(games_with_venues),
        batting_logs=read_csv_table(canonical / "batting_logs.csv"),
        pitcher_logs=read_csv_table(canonical / "pitcher_logs.csv"),
        lineups=read_csv_table(canonical / "lineups.csv"),
        venues=read_csv_table(args.venues),
        park_factors=read_csv_table(park_factors) if park_factors.exists() else None,
    )
    features_path = processed / f"features_confirmed_npb_{args.game_limit}.csv"
    write_csv_table(features, features_path)

    write_feature_quality_report(features, quality)
    write_proeyekyuu_coverage_report(games_with_venues, canonical, root / "npb_proeyekyuu_coverage_report.md")
    write_proeyekyuu_batting_detail_audit(game_tables, root / "npb_proeyekyuu_batting_detail_audit.md")
    feature_set = processed / f"npb_feature_set_{args.game_limit}.csv"
    write_npb_feature_set(features_path, feature_set)
    write_npb_model_ready_features(
        features_path,
        feature_set,
        processed / f"features_confirmed_npb_model_ready_{args.game_limit}.csv",
    )

    print(f"Wrote NPB features: {features_path} ({len(features)} rows)")
    print(f"Wrote quality report: {quality / 'summary.md'}")


if __name__ == "__main__":
    main()
