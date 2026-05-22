"""Run season-holdout model experiments over multiple random seeds."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variants", nargs="+", required=True, help="variant_name=feature_csv")
    parser.add_argument("--models", required=True)
    parser.add_argument("--seeds", default="11,22,33,44,55,66,77,88,99,111")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    parser.add_argument("--baseline-variant", required=True)
    parser.add_argument("--baseline-model", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    variants = []
    for item in args.variants:
        name, path = item.split("=", 1)
        variants.append((name, Path(path)))
    models = parse_csv_strings(args.models)
    seeds = parse_csv_ints(args.seeds)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    rows = []
    for variant_name, feature_path in variants:
        features = read_csv_table(feature_path)
        for seed in seeds:
            for season in holdout_seasons:
                result = run_model_experiments(
                    features,
                    model_names=models,
                    holdout_season=season,
                    prediction_mode=args.prediction_mode,
                    random_state=seed,
                )
                metrics = result.metrics.copy()
                metrics.insert(0, "variant", variant_name)
                metrics.insert(1, "seed", seed)
                metrics.insert(2, "holdout_season", season)
                metrics.insert(3, "feature_count", len(result.feature_columns))
                rows.append(metrics)

    metrics = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    write_csv_table(metrics, output / "metrics_by_seed_holdout.csv")

    summary = (
        metrics.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_log_loss=("log_loss", "mean"),
            std_log_loss=("log_loss", "std"),
            mean_brier_score=("brier_score", "mean"),
            std_brier_score=("brier_score", "std"),
            mean_accuracy=("accuracy", "mean"),
            std_accuracy=("accuracy", "std"),
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
        "# Multi-Seed Model Experiment",
        "",
        f"Baseline: `{args.baseline_variant} + {args.baseline_model}`",
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
    print(f"Wrote multi-seed model experiment to {output}")


if __name__ == "__main__":
    main()
