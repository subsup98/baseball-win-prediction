"""Run feature-group ablation experiments against a full feature table."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments


GROUP_MARKERS = {
    "pitch_stuff": [
        "sp_whiff_rate",
        "sp_avg_fastball_velocity",
        "sp_avg_spin_rate",
        "sp_fastball_usage",
        "sp_breaking_ball_usage",
        "sp_offspeed_usage",
        "sp_fastball_velocity_diff",
        "sp_whiff_rate_diff",
    ],
    "lineup_optional": [
        "lineup_confidence",
        "lineup_available",
        "lineup_expected_starter",
        "lineup_rest_signal",
        "lineup_injury_absence_signal",
        "lineup_previous_starter",
        "lineup_player_count",
    ],
    "travel": [
        "travel_",
    ],
    "bullpen_role": [
        "estimated_high_leverage_role",
    ],
}


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


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def parse_csv_strings(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def matching_columns(columns: list[str], markers: list[str]) -> list[str]:
    return [column for column in columns if any(marker in column for marker in markers)]


def drop_groups(frame: pd.DataFrame, groups: list[str]) -> pd.DataFrame:
    columns = frame.columns.tolist()
    drop_columns: set[str] = set()
    for group in groups:
        drop_columns.update(matching_columns(columns, GROUP_MARKERS[group]))
    return frame.drop(columns=sorted(drop_columns), errors="ignore")


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
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--baseline-features", help="Optional baseline feature table used to define baseline-like columns.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--models", default="random_forest")
    parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    args = parser.parse_args()

    full = read_csv_table(args.features)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    holdout_seasons = parse_csv_ints(args.holdout_seasons)
    model_names = parse_csv_strings(args.models)

    variants: list[tuple[str, pd.DataFrame]] = [("full", full)]
    for group in GROUP_MARKERS:
        variants.append((f"without_{group}", drop_groups(full, [group])))
    variants.append(("without_all_research_groups", drop_groups(full, list(GROUP_MARKERS))))

    if args.baseline_features:
        baseline_columns = read_csv_table(args.baseline_features).columns.tolist()
        keep_columns = [column for column in baseline_columns if column in full.columns]
        variants.append(("baseline_like_columns", full[keep_columns].copy()))

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
    write_csv_table(metrics, output / "feature_group_ablation.csv")

    full_metrics = metrics[metrics["variant"] == "full"][
        ["holdout_season", "model_name", "log_loss", "brier_score", "accuracy"]
    ].rename(
        columns={
            "log_loss": "full_log_loss",
            "brier_score": "full_brier_score",
            "accuracy": "full_accuracy",
        }
    )
    comparison = metrics.merge(full_metrics, on=["holdout_season", "model_name"], how="left")
    comparison["log_loss_delta_vs_full"] = comparison["log_loss"] - comparison["full_log_loss"]
    comparison["brier_score_delta_vs_full"] = comparison["brier_score"] - comparison["full_brier_score"]
    comparison["accuracy_delta_vs_full"] = comparison["accuracy"] - comparison["full_accuracy"]
    write_csv_table(comparison, output / "feature_group_ablation_vs_full.csv")

    summary = (
        comparison.groupby(["variant", "model_name"], as_index=False)
        .agg(
            mean_log_loss=("log_loss", "mean"),
            mean_log_loss_delta_vs_full=("log_loss_delta_vs_full", "mean"),
            mean_accuracy=("accuracy", "mean"),
            mean_accuracy_delta_vs_full=("accuracy_delta_vs_full", "mean"),
            mean_feature_count=("feature_count", "mean"),
        )
        .sort_values(["model_name", "mean_log_loss", "variant"])
    )
    write_csv_table(summary, output / "feature_group_ablation_summary.csv")
    lines = [
        "# Feature Group Ablation",
        "",
        "Positive `mean_log_loss_delta_vs_full` means removing that group made log loss worse, so the group helped the full model.",
        "",
        markdown_table(summary),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote ablation report to {output}")


if __name__ == "__main__":
    main()
