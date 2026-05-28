"""Focused ablation for MLB recent-form feature groups.

The v1 feature pack was too broad. This script keeps the already-built recent
form dataset and creates smaller variants by dropping selected recent-form
columns, so we can test which groups are signal and which are noise.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments


RECENT_PATTERNS = (
    "weighted_win_rate_last_10",
    "weighted_win_rate_last_20",
    "weighted_run_diff_last_10",
    "weighted_run_diff_last_20",
    "weighted_runs_for_last_10",
    "weighted_runs_allowed_last_10",
    "low_run_rate_last_10",
    "5plus_run_rate_last_10",
    "one_run_game_rate_last_20",
    "one_run_win_rate_last_20",
    "runs_for_volatility_last_10",
    "pythagorean_win_pct_last_20",
    "actual_minus_pythag_last_20",
    "close_win_dependency_last_20",
)

V2_CORE_PATTERNS = (
    "weighted_run_diff_last_10",
    "weighted_run_diff_last_20",
    "weighted_runs_for_last_10",
    "weighted_runs_allowed_last_10",
    "low_run_rate_last_10",
    "5plus_run_rate_last_10",
    "actual_minus_pythag_last_20",
)

VARIANT_PATTERNS = {
    "baseline": (),
    "v2_core": V2_CORE_PATTERNS,
    "run_diff_only": ("weighted_run_diff_last_10", "weighted_run_diff_last_20"),
    "scoring_only": (
        "weighted_runs_for_last_10",
        "weighted_runs_allowed_last_10",
        "low_run_rate_last_10",
        "5plus_run_rate_last_10",
    ),
    "pythag_only": ("actual_minus_pythag_last_20", "pythagorean_win_pct_last_20"),
    "weighted_win_only": ("weighted_win_rate_last_10", "weighted_win_rate_last_20"),
    "volatility_only": ("runs_for_volatility_last_10",),
    "close_game_only": (
        "one_run_game_rate_last_20",
        "one_run_win_rate_last_20",
        "close_win_dependency_last_20",
    ),
    "v1_full": RECENT_PATTERNS,
}


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row.tolist()) + " |")
    return "\n".join(lines)


def matching_columns(columns: list[str], patterns: tuple[str, ...]) -> list[str]:
    return [column for column in columns if any(pattern in column for pattern in patterns)]


def variant_frame(features: pd.DataFrame, variant: str) -> pd.DataFrame:
    if variant not in VARIANT_PATTERNS:
        raise ValueError(f"Unknown variant: {variant}")
    columns = list(features.columns)
    recent_columns = matching_columns(columns, RECENT_PATTERNS)
    keep_recent = set(matching_columns(columns, VARIANT_PATTERNS[variant]))
    drop_columns = [column for column in recent_columns if column not in keep_recent]
    return features.drop(columns=drop_columns, errors="ignore")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features",
        default="data/processed/features_confirmed_2021_2025_with_park_factors_statcast_recent_form.csv",
    )
    parser.add_argument("--output-dir", default="outputs/experiments/mlb_recent_form_v2_ablation_2021_2025")
    parser.add_argument("--variants", default=",".join(VARIANT_PATTERNS))
    parser.add_argument("--models", default="random_forest_shallow,random_forest")
    parser.add_argument("--seeds", default="11,22,33")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    parser.add_argument("--baseline-variant", default="baseline")
    parser.add_argument("--baseline-model", default="random_forest")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    output = Path(args.output_dir)
    variants_dir = output / "feature_variants"
    variants_dir.mkdir(parents=True, exist_ok=True)
    models = parse_csv_strings(args.models)
    variants = parse_csv_strings(args.variants)
    seeds = parse_csv_ints(args.seeds)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)

    variant_counts = []
    rows = []
    for variant in variants:
        frame = variant_frame(features, variant)
        variant_path = variants_dir / f"{variant}.csv"
        write_csv_table(frame, variant_path)
        variant_counts.append(
            {
                "variant": variant,
                "rows": len(frame),
                "columns": frame.shape[1],
                "recent_columns_kept": len(matching_columns(list(frame.columns), RECENT_PATTERNS)),
            }
        )
        for seed in seeds:
            for season in holdout_seasons:
                result = run_model_experiments(
                    frame,
                    model_names=models,
                    holdout_season=season,
                    prediction_mode=args.prediction_mode,
                    random_state=seed,
                )
                metrics = result.metrics.copy()
                metrics.insert(0, "variant", variant)
                metrics.insert(1, "seed", seed)
                metrics.insert(2, "holdout_season", season)
                metrics.insert(3, "feature_count", len(result.feature_columns))
                rows.append(metrics)

    metrics = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    write_csv_table(metrics, output / "metrics_by_seed_holdout.csv")
    write_csv_table(pd.DataFrame(variant_counts), output / "variant_feature_counts.csv")

    summary = (
        metrics.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_log_loss=("log_loss", "mean"),
            std_log_loss=("log_loss", "std"),
            mean_brier_score=("brier_score", "mean"),
            mean_accuracy=("accuracy", "mean"),
            mean_accuracy_conf_60=("accuracy_conf_60", "mean"),
            mean_coverage_conf_60=("coverage_conf_60", "mean"),
            mean_feature_count=("feature_count", "mean"),
        )
        .sort_values(["mean_log_loss", "mean_brier_score", "variant", "model_name"])
    )
    write_csv_table(summary, output / "summary_by_variant_model.csv")

    baseline = metrics[
        (metrics["variant"] == args.baseline_variant)
        & (metrics["model_name"] == args.baseline_model)
    ][["seed", "holdout_season", "log_loss", "brier_score", "accuracy"]].rename(
        columns={
            "log_loss": "baseline_log_loss",
            "brier_score": "baseline_brier_score",
            "accuracy": "baseline_accuracy",
        }
    )
    comparison = metrics.merge(baseline, on=["seed", "holdout_season"], how="left")
    comparison["log_loss_delta_vs_baseline"] = comparison["log_loss"] - comparison["baseline_log_loss"]
    comparison["accuracy_delta_vs_baseline"] = comparison["accuracy"] - comparison["baseline_accuracy"]
    write_csv_table(comparison, output / "metrics_vs_baseline.csv")

    stability = (
        comparison.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_log_loss_delta_vs_baseline=("log_loss_delta_vs_baseline", "mean"),
            median_log_loss_delta_vs_baseline=("log_loss_delta_vs_baseline", "median"),
            log_loss_win_rate_vs_baseline=("log_loss_delta_vs_baseline", lambda values: float((values < 0).mean())),
            mean_accuracy_delta_vs_baseline=("accuracy_delta_vs_baseline", "mean"),
            accuracy_win_rate_vs_baseline=("accuracy_delta_vs_baseline", lambda values: float((values > 0).mean())),
        )
        .sort_values(["mean_log_loss_delta_vs_baseline", "variant", "model_name"])
    )
    write_csv_table(stability, output / "stability_vs_baseline.csv")

    lines = [
        "# MLB Recent Form v2 Ablation",
        "",
        f"Baseline: `{args.baseline_variant} + {args.baseline_model}`",
        "",
        "## Variant Feature Counts",
        "",
        markdown_table(pd.DataFrame(variant_counts)),
        "",
        "## Summary By Variant And Model",
        "",
        markdown_table(summary),
        "",
        "## Stability Vs Baseline",
        "",
        markdown_table(stability),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote MLB recent form v2 ablation to {output}")


if __name__ == "__main__":
    main()
