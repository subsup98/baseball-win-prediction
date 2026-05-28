"""Compare score/expected-runs regression models across season holdouts.

Item: "Compare score model alternatives beyond current random forest regressor".

Reuses ``run_expected_runs_experiments`` to evaluate several regressors on
2022-2025 season holdouts, reporting home/away/total/run_diff MAE+RMSE and the
synthetic over/under accuracy. Booster regressors are skipped gracefully if the
optional dependency is not installed.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import write_csv_table
from mlb_winprob.experiments import run_expected_runs_experiments
from mlb_winprob.models import ModelUnavailableError
from mlb_winprob.reporting import read_feature_tables


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_csv_floats(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--features",
        nargs="+",
        default=["data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv"],
    )
    parser.add_argument("--output-dir", default="outputs/experiments/score_model_comparison_confirmed_2021_2025")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument(
        "--models",
        default="ridge,random_forest_regressor,gradient_boosting_regressor,hist_gradient_boosting_regressor,lightgbm_regressor,catboost_regressor",
    )
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    parser.add_argument("--synthetic-total-lines", default="7.5,8.5,9.5")
    args = parser.parse_args()

    features = read_feature_tables(args.features)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    requested_models = parse_csv_strings(args.models)
    total_lines = parse_csv_floats(args.synthetic_total_lines)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    # Probe model availability once so unavailable boosters are dropped cleanly.
    available_models: list[str] = []
    for model_name in requested_models:
        try:
            run_expected_runs_experiments(
                features,
                model_names=[model_name],
                holdout_season=holdout_seasons[0],
                prediction_mode=args.prediction_mode,
                synthetic_total_lines=total_lines,
            )
        except ModelUnavailableError as exc:
            print(f"Skipping unavailable model '{model_name}': {exc}")
            continue
        available_models.append(model_name)

    metrics_frames = []
    ou_frames = []
    for season in holdout_seasons:
        result = run_expected_runs_experiments(
            features,
            model_names=available_models,
            holdout_season=season,
            prediction_mode=args.prediction_mode,
            synthetic_total_lines=total_lines,
        )
        m = result.metrics.copy()
        m.insert(0, "holdout_season", season)
        metrics_frames.append(m)
        ou = result.synthetic_ou_metrics.copy()
        ou.insert(0, "holdout_season", season)
        ou_frames.append(ou)

    metrics = pd.concat(metrics_frames, ignore_index=True)
    ou_metrics = pd.concat(ou_frames, ignore_index=True)
    write_csv_table(metrics, output / "expected_runs_metrics_by_holdout.csv")
    write_csv_table(ou_metrics, output / "synthetic_ou_metrics_by_holdout.csv")

    model_summary = (
        metrics.groupby("model_name", as_index=False)
        .agg(
            mean_total_mae=("total_mae", "mean"),
            mean_total_rmse=("total_rmse", "mean"),
            mean_home_mae=("home_mae", "mean"),
            mean_away_mae=("away_mae", "mean"),
            mean_run_diff_mae=("run_diff_mae", "mean"),
            mean_total_within_1=("total_within_1", "mean"),
            mean_total_within_2=("total_within_2", "mean"),
        )
        .sort_values(["mean_total_mae", "mean_total_rmse"])
    )
    write_csv_table(model_summary, output / "model_summary.csv")

    best_by_season = (
        metrics.sort_values(["holdout_season", "total_mae", "total_rmse"])
        .groupby("holdout_season", as_index=False)
        .head(1)
        .reset_index(drop=True)
    )
    write_csv_table(best_by_season, output / "best_by_holdout.csv")

    # Mean OU accuracy at the central 8.5 line by model.
    ou_85 = (
        ou_metrics[ou_metrics["total_line"] == 8.5]
        .groupby("model_name", as_index=False)
        .agg(mean_ou_accuracy_8_5=("ou_accuracy", "mean"))
        .sort_values("mean_ou_accuracy_8_5", ascending=False)
    )

    lines = [
        "# Score Model Comparison (Expected Runs)",
        "",
        f"Models: {', '.join(available_models)}",
        f"Holdouts: {', '.join(map(str, holdout_seasons))}",
        "",
        "## Mean Metrics By Model (lower MAE/RMSE is better)",
        "",
        markdown_table(model_summary.round(4)),
        "",
        "## Mean Synthetic O/U Accuracy At 8.5 Line",
        "",
        markdown_table(ou_85.round(4)),
        "",
        "## Best Model Per Holdout (by total_mae)",
        "",
        markdown_table(best_by_season[["holdout_season", "model_name", "total_mae", "total_rmse"]].round(4)),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    print("\n=== Mean metrics by model ===")
    with pd.option_context("display.width", 180, "display.max_columns", 20):
        print(model_summary.round(4).to_string(index=False))
    print("\n=== Mean O/U accuracy at 8.5 ===")
    print(ou_85.round(4).to_string(index=False))
    print(f"\nWrote score model comparison to {output}")


if __name__ == "__main__":
    main()
