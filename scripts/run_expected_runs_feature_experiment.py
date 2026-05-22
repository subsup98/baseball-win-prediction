"""Test holdout-safe expected-run predictions as win-probability features."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import add_expected_runs_prediction_features, run_model_experiments


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


def run_holdouts(
    features: pd.DataFrame,
    *,
    holdout_seasons: list[int],
    models: list[str],
    prediction_mode: str,
    label: str,
) -> pd.DataFrame:
    rows = []
    for season in holdout_seasons:
        result = run_model_experiments(
            features,
            model_names=models,
            holdout_season=season,
            prediction_mode=prediction_mode,
        )
        metrics = result.metrics.copy()
        metrics.insert(0, "feature_set", label)
        metrics.insert(1, "holdout_season", season)
        metrics.insert(2, "feature_count", len(result.feature_columns))
        rows.append(metrics)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--models", default="random_forest")
    parser.add_argument("--expected-runs-model", default="ridge")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    model_names = parse_csv_strings(args.models)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    augmented = add_expected_runs_prediction_features(
        features,
        holdout_seasons=holdout_seasons,
        model_name=args.expected_runs_model,
        prediction_mode=args.prediction_mode,
    )
    write_csv_table(augmented, output / "features_with_expected_runs_oof.csv")

    baseline_metrics = run_holdouts(
        features,
        holdout_seasons=holdout_seasons,
        models=model_names,
        prediction_mode=args.prediction_mode,
        label="baseline",
    )
    augmented_metrics = run_holdouts(
        augmented,
        holdout_seasons=holdout_seasons,
        models=model_names,
        prediction_mode=args.prediction_mode,
        label=f"expected_runs_{args.expected_runs_model}",
    )
    metrics = pd.concat([baseline_metrics, augmented_metrics], ignore_index=True)
    write_csv_table(metrics, output / "metrics_by_holdout.csv")

    baseline = baseline_metrics[
        ["holdout_season", "model_name", "log_loss", "brier_score", "accuracy", "accuracy_conf_60", "coverage_conf_60"]
    ].rename(
        columns={
            "log_loss": "baseline_log_loss",
            "brier_score": "baseline_brier_score",
            "accuracy": "baseline_accuracy",
            "accuracy_conf_60": "baseline_accuracy_conf_60",
            "coverage_conf_60": "baseline_coverage_conf_60",
        }
    )
    comparison = augmented_metrics.merge(baseline, on=["holdout_season", "model_name"], how="left")
    comparison["log_loss_delta_vs_baseline"] = comparison["log_loss"] - comparison["baseline_log_loss"]
    comparison["brier_score_delta_vs_baseline"] = comparison["brier_score"] - comparison["baseline_brier_score"]
    comparison["accuracy_delta_vs_baseline"] = comparison["accuracy"] - comparison["baseline_accuracy"]
    comparison["accuracy_conf_60_delta_vs_baseline"] = (
        comparison["accuracy_conf_60"] - comparison["baseline_accuracy_conf_60"]
    )
    comparison["coverage_conf_60_delta_vs_baseline"] = (
        comparison["coverage_conf_60"] - comparison["baseline_coverage_conf_60"]
    )
    write_csv_table(comparison, output / "metrics_vs_baseline.csv")

    summary = (
        comparison.groupby("model_name", as_index=False)
        .agg(
            mean_log_loss_delta_vs_baseline=("log_loss_delta_vs_baseline", "mean"),
            mean_brier_score_delta_vs_baseline=("brier_score_delta_vs_baseline", "mean"),
            mean_accuracy_delta_vs_baseline=("accuracy_delta_vs_baseline", "mean"),
            mean_accuracy_conf_60_delta_vs_baseline=("accuracy_conf_60_delta_vs_baseline", "mean"),
            mean_coverage_conf_60_delta_vs_baseline=("coverage_conf_60_delta_vs_baseline", "mean"),
        )
        .sort_values(["mean_log_loss_delta_vs_baseline", "model_name"])
    )
    write_csv_table(summary, output / "summary_by_model.csv")

    lines = [
        "# Expected-Runs Feature Experiment",
        "",
        f"Expected-runs model: `{args.expected_runs_model}`",
        "",
        "## Summary By Model",
        "",
        markdown_table(summary),
        "",
        "## Metrics Vs Baseline",
        "",
        markdown_table(comparison),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote expected-runs feature experiment to {output}")


if __name__ == "__main__":
    main()
