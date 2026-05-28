"""Compare KBO feature stages with multi-seed season holdouts."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments


ENV_PATTERNS = (
    "venue_",
    "travel_",
    "park_factor_",
    "temperature",
    "wind_",
    "humidity",
    "is_dome",
)

PUBLIC_PROXY_PATTERNS = (
    "_proxy",
    "babip",
    "bb_rate",
    "k_rate",
    "k_per_9",
    "bb_per_9",
    "hr_per_9",
    "sp_era",
    "lineup_avg_iso",
    "lineup_avg_babip",
    "lineup_iso_diff",
    "team_bb_rate",
    "team_k_rate",
)


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


def write_variant_features(features: pd.DataFrame, output: Path) -> dict[str, Path]:
    output.mkdir(parents=True, exist_ok=True)
    columns = list(features.columns)
    env_columns = matching_columns(columns, ENV_PATTERNS)
    public_proxy_columns = matching_columns(columns, PUBLIC_PROXY_PATTERNS)

    variants = {
        "full": features,
        "no_env": features.drop(columns=env_columns, errors="ignore"),
        "no_public_proxy": features.drop(columns=public_proxy_columns, errors="ignore"),
        "baseline_like": features.drop(columns=sorted(set(env_columns + public_proxy_columns)), errors="ignore"),
    }
    paths: dict[str, Path] = {}
    rows = []
    for name, frame in variants.items():
        path = output / f"{name}.csv"
        write_csv_table(frame, path)
        paths[name] = path
        rows.append(
            {
                "variant": name,
                "rows": len(frame),
                "columns": frame.shape[1],
                "dropped_vs_full": features.shape[1] - frame.shape[1],
            }
        )
    write_csv_table(pd.DataFrame(rows), output / "variant_feature_counts.csv")
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default="data/processed/kbo/features_confirmed_kbo_2021_2026.csv")
    parser.add_argument("--output-dir", default="outputs/experiments/kbo/feature_stage_multiseed_kbo_2021_2026")
    parser.add_argument("--models", default="random_forest_shallow,random_forest,extra_trees")
    parser.add_argument("--seeds", default="11,22,33")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025,2026")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    output = Path(args.output_dir)
    variants_dir = output / "feature_variants"
    variant_paths = write_variant_features(features, variants_dir)
    models = parse_csv_strings(args.models)
    seeds = parse_csv_ints(args.seeds)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)

    rows = []
    for variant, path in variant_paths.items():
        variant_features = read_csv_table(path)
        for seed in seeds:
            for season in holdout_seasons:
                result = run_model_experiments(
                    variant_features,
                    model_names=models,
                    holdout_season=season,
                    prediction_mode="confirmed_lineup",
                    random_state=seed,
                )
                metrics = result.metrics.copy()
                metrics.insert(0, "variant", variant)
                metrics.insert(1, "seed", seed)
                metrics.insert(2, "holdout_season", season)
                metrics.insert(3, "feature_count", len(result.feature_columns))
                rows.append(metrics)

    metrics = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    output.mkdir(parents=True, exist_ok=True)
    write_csv_table(metrics, output / "metrics_by_seed_holdout.csv")

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
        (metrics["variant"] == "baseline_like")
        & (metrics["model_name"] == "random_forest_shallow")
    ][["seed", "holdout_season", "log_loss", "accuracy"]].rename(
        columns={"log_loss": "baseline_log_loss", "accuracy": "baseline_accuracy"}
    )
    comparison = metrics.merge(baseline, on=["seed", "holdout_season"], how="left")
    comparison["log_loss_delta_vs_baseline"] = comparison["log_loss"] - comparison["baseline_log_loss"]
    comparison["accuracy_delta_vs_baseline"] = comparison["accuracy"] - comparison["baseline_accuracy"]
    write_csv_table(comparison, output / "metrics_vs_baseline.csv")

    lift = (
        comparison.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_log_loss_delta_vs_baseline=("log_loss_delta_vs_baseline", "mean"),
            log_loss_win_rate_vs_baseline=("log_loss_delta_vs_baseline", lambda values: float((values < 0).mean())),
            mean_accuracy_delta_vs_baseline=("accuracy_delta_vs_baseline", "mean"),
        )
        .sort_values(["mean_log_loss_delta_vs_baseline", "variant", "model_name"])
    )
    write_csv_table(lift, output / "lift_vs_baseline.csv")

    lines = [
        "# KBO Feature Stage Multi-Seed Experiment",
        "",
        "Baseline comparison uses `baseline_like + random_forest_shallow`.",
        "",
        "## Summary By Variant And Model",
        "",
        markdown_table(summary),
        "",
        "## Lift Vs Baseline",
        "",
        markdown_table(lift),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote KBO feature stage experiment to {output}")


if __name__ == "__main__":
    main()
