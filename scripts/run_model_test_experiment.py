"""Run lightweight season-holdout model tests without SHAP/importance outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.evaluation import model_selection_rules
from mlb_winprob.experiments import run_model_experiments
from mlb_winprob.reporting import read_feature_tables


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
    parser.add_argument("--features", nargs="+", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--models", required=True)
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    args = parser.parse_args()

    features = read_feature_tables(args.features)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    model_names = parse_csv_strings(args.models)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    frames = []
    feature_counts = []
    for season in holdout_seasons:
        result = run_model_experiments(
            features,
            model_names=model_names,
            holdout_season=season,
            prediction_mode=args.prediction_mode,
        )
        metrics = result.metrics.copy()
        metrics.insert(0, "holdout_season", season)
        frames.append(metrics)
        feature_counts.append({"holdout_season": season, "feature_count": len(result.feature_columns)})

    metrics = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    best = (
        metrics.sort_values(["holdout_season", "log_loss", "brier_score"])
        .groupby("holdout_season", as_index=False)
        .head(1)
        .reset_index(drop=True)
        if not metrics.empty
        else pd.DataFrame()
    )
    mean_by_model = (
        metrics.groupby("model_name", as_index=False)
        .agg(
            mean_log_loss=("log_loss", "mean"),
            mean_brier_score=("brier_score", "mean"),
            mean_accuracy=("accuracy", "mean"),
            mean_accuracy_conf_60=("accuracy_conf_60", "mean"),
            mean_coverage_conf_60=("coverage_conf_60", "mean"),
        )
        .sort_values(["mean_log_loss", "mean_brier_score", "model_name"])
        if not metrics.empty
        else pd.DataFrame()
    )
    selection = model_selection_rules(metrics) if not metrics.empty else pd.DataFrame()

    paths = {
        "metrics": output / "metrics_by_holdout.csv",
        "best": output / "best_by_holdout.csv",
        "mean": output / "mean_by_model.csv",
        "selection": output / "model_selection_rules.csv",
        "features": output / "feature_counts.csv",
    }
    write_csv_table(metrics, paths["metrics"])
    write_csv_table(best, paths["best"])
    write_csv_table(mean_by_model, paths["mean"])
    write_csv_table(selection, paths["selection"])
    write_csv_table(pd.DataFrame(feature_counts), paths["features"])

    lines = [
        "# Model Test Experiment",
        "",
        f"Models: `{', '.join(model_names)}`",
        "",
        "## Mean By Model",
        "",
        markdown_table(mean_by_model),
        "",
        "## Best By Holdout",
        "",
        markdown_table(best),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote model test experiment to {output}")


if __name__ == "__main__":
    main()
