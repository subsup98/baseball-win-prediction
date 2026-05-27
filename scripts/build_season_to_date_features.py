"""Build a leakage-safe season-to-date feature table from a snapshot directory.

Unlike ``build_statcast_feature_pipeline.py`` (which assumes the full-season
``data/standardized/mlb_stats_api_<season>`` layout), this script accepts an
explicit standardized snapshot directory such as
``data/season_to_date/mlb_stats_api_2026_to_2026-05-26/standardized``.

It exists to replace the earlier 2026 "compatibility" path that fed prior-season
(2025) logs into the feature builder. Here the in-season logs from the snapshot
are used directly, so all rolling / season-to-date features are computed from
real same-season games and remain leakage-safe (each game excludes itself).

When a Statcast raw CSV for the snapshot is provided, its quality columns are
merged into the logs so the output schema matches the Statcast-enriched models.
Without it, Statcast feature columns are written as missing values so the
column set still aligns with the trained model schema.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.features import FeatureBuildConfig, FeatureBuilder
from mlb_winprob.reporting import write_feature_quality_report
from mlb_winprob.statcast import (
    aggregate_statcast_batting,
    aggregate_statcast_pitching,
    merge_statcast_quality,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--standardized-dir",
        default="data/season_to_date/mlb_stats_api_2026_to_2026-05-26/standardized",
        help="Directory holding games/batting_logs/pitcher_logs/lineups/weather CSVs.",
    )
    parser.add_argument("--season", type=int, default=2026)
    parser.add_argument(
        "--statcast-raw",
        default="data/raw/statcast/statcast_2026.csv",
        help="Optional Statcast event CSV for the snapshot. Skipped if missing.",
    )
    parser.add_argument(
        "--park-factors",
        default="data/processed/park_factors_empirical_previous_season_2022_2026.csv",
    )
    parser.add_argument("--venues", default="data/raw/mlb_stats_api/venues_2021_2025.csv")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    parser.add_argument(
        "--output",
        default="data/processed/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast.csv",
    )
    parser.add_argument(
        "--quality-output",
        default="outputs/quality/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast",
    )
    parser.add_argument(
        "--reference-features",
        default="data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv",
        help="Training feature table used to align/verify the output column schema.",
    )
    parser.add_argument("--statcast-quality-dir", default=None, help="Where to write aggregated Statcast quality CSVs.")
    return parser.parse_args()


ID_COLUMNS = ["game_id", "player_id", "home_sp_id", "away_sp_id"]


def _norm_id_series(series: pd.Series) -> pd.Series:
    """Canonicalize an id column to a plain string (e.g. 12345.0 -> "12345").

    Statcast aggregation/merge forces game_id/player_id/team to ``astype(str)``,
    while numeric-only snapshot CSVs are inferred as int64/float64. Without a
    shared representation the downstream merges inside FeatureBuilder fail with
    "merge on float64 and str columns". Non-numeric ids are preserved as-is.
    """

    numeric = pd.to_numeric(series, errors="coerce")
    result = numeric.astype("Int64").astype("string")
    fallback = series.isna().eq(False) & result.isna()
    if fallback.any():
        result[fallback] = series.astype("string")[fallback]
    return result


def _normalize_ids(frame: pd.DataFrame) -> pd.DataFrame:
    """Apply :func:`_norm_id_series` to every known id column present."""

    frame = frame.copy()
    for column in ID_COLUMNS:
        if column in frame.columns:
            frame[column] = _norm_id_series(frame[column])
    return frame


def maybe_enrich_logs(
    standardized_dir: Path,
    statcast_raw: Path | None,
    quality_dir: Path,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    """Return (batting_logs, pitcher_logs, statcast_used)."""

    batting_logs = read_csv_table(standardized_dir / "batting_logs.csv")
    pitcher_logs = read_csv_table(standardized_dir / "pitcher_logs.csv")

    if statcast_raw is None or not statcast_raw.exists():
        print(f"Statcast raw not found ({statcast_raw}); building without Statcast quality columns.")
        return batting_logs, pitcher_logs, False

    print(f"Aggregating Statcast quality from {statcast_raw} ...")
    events = read_csv_table(statcast_raw)
    statcast_batting = aggregate_statcast_batting(events)
    statcast_pitching = aggregate_statcast_pitching(events)
    quality_dir.mkdir(parents=True, exist_ok=True)
    write_csv_table(statcast_batting, quality_dir / "batting_quality.csv")
    write_csv_table(statcast_pitching, quality_dir / "pitching_quality.csv")
    print(f"Statcast quality rows: batting={len(statcast_batting)} pitching={len(statcast_pitching)}")

    batting_logs, pitcher_logs = merge_statcast_quality(
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        statcast_batting=statcast_batting,
        statcast_pitching=statcast_pitching,
    )
    return batting_logs, pitcher_logs, True


def align_to_reference(features: pd.DataFrame, reference_path: Path) -> pd.DataFrame:
    """Add any training columns missing from the snapshot as NaN and report the diff."""

    if not reference_path.exists():
        print(f"Reference feature table not found ({reference_path}); skipping schema alignment.")
        return features

    reference_columns = list(pd.read_csv(reference_path, nrows=0).columns)
    snapshot_columns = list(features.columns)

    missing = [col for col in reference_columns if col not in snapshot_columns]
    extra = [col for col in snapshot_columns if col not in reference_columns]

    if missing:
        print(f"Adding {len(missing)} missing training columns as NaN: {missing[:10]}{' ...' if len(missing) > 10 else ''}")
        for col in missing:
            features[col] = pd.NA
    if extra:
        print(f"Snapshot has {len(extra)} columns not in training schema (kept): {extra[:10]}{' ...' if len(extra) > 10 else ''}")

    ordered = [col for col in reference_columns if col in features.columns]
    ordered += [col for col in features.columns if col not in reference_columns]
    return features[ordered]


def main() -> None:
    args = parse_args()
    standardized_dir = Path(args.standardized_dir)
    statcast_raw = Path(args.statcast_raw) if args.statcast_raw else None
    quality_dir = Path(args.statcast_quality_dir) if args.statcast_quality_dir else standardized_dir / "statcast_quality"

    print(f"Standardized snapshot: {standardized_dir}")
    print(f"Season: {args.season}  prediction_mode: {args.prediction_mode}")

    batting_logs, pitcher_logs, statcast_used = maybe_enrich_logs(standardized_dir, statcast_raw, quality_dir)

    venues_path = Path(args.venues)
    park_factors_path = Path(args.park_factors)

    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode=args.prediction_mode))
    features = builder.build(
        games=_normalize_ids(read_csv_table(standardized_dir / "games.csv")),
        batting_logs=_normalize_ids(batting_logs),
        pitcher_logs=_normalize_ids(pitcher_logs),
        lineups=_normalize_ids(read_csv_table(standardized_dir / "lineups.csv")),
        weather=_normalize_ids(read_csv_table(standardized_dir / "weather.csv")),
        park_factors=read_csv_table(park_factors_path) if park_factors_path.exists() else None,
        venues=read_csv_table(venues_path) if venues_path.exists() else None,
    )
    print(f"Built feature rows={len(features)} columns={features.shape[1]} statcast_used={statcast_used}")

    features = align_to_reference(features, Path(args.reference_features))

    output = Path(args.output)
    write_csv_table(features, output)
    print(f"Wrote features -> {output} (rows={len(features)} columns={features.shape[1]})")

    quality_output = Path(args.quality_output)
    write_feature_quality_report(features, quality_output)
    print(f"Wrote quality report -> {quality_output}")


if __name__ == "__main__":
    main()
