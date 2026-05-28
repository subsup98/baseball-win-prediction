"""Group-level ablation driven by feature-stability results.

Item: "Stable feature group ablation" - instead of deleting one-off features,
form groups from the feature-stability summary and measure each group's log-loss
impact on the full model.

Inputs (from scripts/summarize_feature_stability.py):
- stable_features_intersection.csv  -> features stably important across seasons
- low_stability_watch_features.csv  -> features whose importance is unstable

Variants evaluated per holdout season (vs full):
- full                  : all features (current baseline).
- without_low_stability : drop the low-stability watch group (pruning candidate).
- without_stable        : drop the stable group (diagnostic; expected to hurt).
- stable_only           : keep only the stable group (how much the rest adds).

Positive ``mean_log_loss_delta_vs_full`` means removing that group made log loss
worse, i.e. the dropped group was helping the full model.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments, select_feature_columns


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
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row.tolist()) + " |")
    return "\n".join(lines)


def load_group(path: Path, column: str, available: set[str]) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Missing stability file: {path}")
    frame = read_csv_table(path)
    if column not in frame.columns:
        column = frame.columns[0]
    members = [str(value) for value in frame[column].dropna().tolist()]
    present = [m for m in members if m in available]
    print(f"{path.name}: {len(present)}/{len(members)} group members present in feature table")
    return present


def run_variant(
    *,
    name: str,
    frame: pd.DataFrame,
    holdout_seasons: list[int],
    model_names: list[str],
    prediction_mode: str | None,
) -> pd.DataFrame:
    rows = []
    for season in holdout_seasons:
        result = run_model_experiments(
            frame,
            model_names=model_names,
            holdout_season=season,
            prediction_mode=prediction_mode,
        )
        metrics = result.metrics.copy()
        metrics.insert(0, "variant", name)
        metrics.insert(1, "holdout_season", season)
        metrics.insert(2, "feature_count", len(result.feature_columns))
        rows.append(metrics)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features", default="data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv")
    parser.add_argument("--stability-dir", default="outputs/experiments/feature_stability_confirmed_2021_2025")
    parser.add_argument("--output-dir", default="outputs/experiments/stable_group_ablation_confirmed_2021_2025")
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--models", default="random_forest")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    args = parser.parse_args()

    full = read_csv_table(args.features)
    feature_columns = set(select_feature_columns(full))
    stability_dir = Path(args.stability_dir)
    stable = load_group(stability_dir / "stable_features_intersection.csv", "stable_feature", feature_columns)
    low = load_group(stability_dir / "low_stability_watch_features.csv", "watch_feature", feature_columns)

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    model_names = parse_csv_strings(args.models)

    # Drop only numeric feature columns; meta/target columns are preserved.
    stable_only_drop = [c for c in feature_columns if c not in set(stable)]
    variants: list[tuple[str, pd.DataFrame]] = [
        ("full", full),
        ("without_low_stability", full.drop(columns=low, errors="ignore")),
        ("without_stable", full.drop(columns=stable, errors="ignore")),
        ("stable_only", full.drop(columns=stable_only_drop, errors="ignore")),
    ]

    metrics = pd.concat(
        [
            run_variant(
                name=name,
                frame=frame,
                holdout_seasons=holdout_seasons,
                model_names=model_names,
                prediction_mode=args.prediction_mode,
            )
            for name, frame in variants
        ],
        ignore_index=True,
    )
    write_csv_table(metrics, output / "stable_group_ablation.csv")

    full_metrics = metrics[metrics["variant"] == "full"][
        ["holdout_season", "model_name", "log_loss", "brier_score", "accuracy"]
    ].rename(columns={"log_loss": "full_log_loss", "brier_score": "full_brier_score", "accuracy": "full_accuracy"})
    comparison = metrics.merge(full_metrics, on=["holdout_season", "model_name"], how="left")
    comparison["log_loss_delta_vs_full"] = comparison["log_loss"] - comparison["full_log_loss"]
    comparison["accuracy_delta_vs_full"] = comparison["accuracy"] - comparison["full_accuracy"]
    write_csv_table(comparison, output / "stable_group_ablation_vs_full.csv")

    summary = (
        comparison.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_feature_count=("feature_count", "mean"),
            mean_log_loss=("log_loss", "mean"),
            mean_log_loss_delta_vs_full=("log_loss_delta_vs_full", "mean"),
            mean_accuracy=("accuracy", "mean"),
            mean_accuracy_delta_vs_full=("accuracy_delta_vs_full", "mean"),
        )
        .sort_values(["model_name", "mean_log_loss", "variant"])
    )
    write_csv_table(summary, output / "stable_group_ablation_summary.csv")

    lines = [
        "# Stable Feature Group Ablation",
        "",
        f"Stable group: {len(stable)} features. Low-stability group: {len(low)} features.",
        "",
        "Positive `mean_log_loss_delta_vs_full` means removing that group made log loss worse "
        "(the group was helping the full model).",
        "",
        markdown_table(summary.round(6)),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n=== summary ===")
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(summary.round(6).to_string(index=False))
    print(f"\nWrote ablation report to {output}")


if __name__ == "__main__":
    main()
