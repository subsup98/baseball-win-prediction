"""Evaluate recent-season training challengers against the 2021-2025 baseline.

Motivation: the production win model trains on all of 2021-2025. If the league /
roster distribution has drifted, a model trained only on recent seasons (or one
that down-weights older seasons) might track the current 2026 season better.

This script trains three Random Forest variants on the historical feature table
and scores each on the leakage-safe 2026 season-to-date table (scored games):

1. ``baseline_rf_2021_2025``        - all seasons, equal weight (current default).
2. ``challenger_rf_2024_2025``      - trained on 2024-2025 only.
3. ``recency_weighted_rf``          - all seasons with exponential season weights.

All three share the same feature column set (selected on the full baseline) for a
fair comparison. A 2025-holdout sanity check is also reported so we can tell
whether any 2026 gain is real signal or just a smaller-sample artifact.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.evaluation import evaluate_probabilities
from mlb_winprob.experiments import select_feature_columns
from mlb_winprob.models import make_classifier

REPORT_METRICS = [
    "n_games",
    "log_loss",
    "brier_score",
    "accuracy",
    "accuracy_conf_60",
    "coverage_conf_60",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-features",
        default="data/processed/features_confirmed_2021_2025_with_park_factors_statcast.csv",
    )
    parser.add_argument(
        "--target-features",
        default="data/processed/features_confirmed_2026_to_2026-05-26_with_park_factors_statcast.csv",
    )
    parser.add_argument("--recent-seasons", default="2024,2025", help="Seasons for the recency challenger.")
    parser.add_argument("--latest-season", type=int, default=2025, help="Most recent training season (weight anchor).")
    parser.add_argument("--half-life", type=float, default=2.0, help="Recency weight half-life in seasons.")
    parser.add_argument("--model-name", default="random_forest")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--prediction-mode", default="confirmed_lineup")
    parser.add_argument("--output-dir", default="outputs/experiments/recent_season_challenger_2026")
    return parser.parse_args()


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def scored_frame(features: pd.DataFrame, prediction_mode: str | None) -> pd.DataFrame:
    frame = features
    if prediction_mode and "prediction_mode" in frame.columns:
        frame = frame[frame["prediction_mode"] == prediction_mode]
    frame = frame.dropna(subset=["home_team_win"]).copy()
    return frame


def recency_weights(seasons: pd.Series, latest_season: int, half_life: float) -> np.ndarray:
    age = latest_season - seasons.astype(float)
    return np.power(0.5, age / half_life).to_numpy()


def fit_and_score(
    model_name: str,
    train_x: pd.DataFrame,
    train_y: pd.Series,
    eval_x: pd.DataFrame,
    eval_y: pd.Series,
    *,
    random_state: int,
    sample_weight: np.ndarray | None = None,
) -> dict[str, float]:
    estimator = make_classifier(model_name, random_state=random_state)
    if sample_weight is not None:
        estimator.fit(train_x, train_y, model__sample_weight=sample_weight)
    else:
        estimator.fit(train_x, train_y)
    probability = estimator.predict_proba(eval_x)[:, 1]
    metrics = evaluate_probabilities(eval_y, probability)
    metrics["train_rows"] = float(len(train_x))
    return metrics


def evaluate_variants(
    baseline_train: pd.DataFrame,
    eval_frame: pd.DataFrame,
    feature_columns: list[str],
    recent_seasons: list[int],
    args: argparse.Namespace,
    *,
    eval_label: str,
) -> pd.DataFrame:
    eval_x = eval_frame[feature_columns]
    eval_y = eval_frame["home_team_win"].astype(int)

    rows: list[dict[str, object]] = []

    # 1. baseline: all training seasons, equal weight
    rows.append(
        {
            "eval_set": eval_label,
            "model": "baseline_rf_all_seasons",
            **fit_and_score(
                args.model_name,
                baseline_train[feature_columns],
                baseline_train["home_team_win"].astype(int),
                eval_x,
                eval_y,
                random_state=args.random_state,
            ),
        }
    )

    # 2. challenger: recent seasons only
    recent_train = baseline_train[baseline_train["season"].isin(recent_seasons)]
    rows.append(
        {
            "eval_set": eval_label,
            "model": f"challenger_rf_{'_'.join(map(str, recent_seasons))}",
            **fit_and_score(
                args.model_name,
                recent_train[feature_columns],
                recent_train["home_team_win"].astype(int),
                eval_x,
                eval_y,
                random_state=args.random_state,
            ),
        }
    )

    # 3. recency-weighted: all seasons, exponential weight
    weights = recency_weights(baseline_train["season"], args.latest_season, args.half_life)
    rows.append(
        {
            "eval_set": eval_label,
            "model": f"recency_weighted_rf_hl{args.half_life:g}",
            **fit_and_score(
                args.model_name,
                baseline_train[feature_columns],
                baseline_train["home_team_win"].astype(int),
                eval_x,
                eval_y,
                random_state=args.random_state,
                sample_weight=weights,
            ),
        }
    )

    return pd.DataFrame(rows)


def main() -> None:
    args = parse_args()
    recent_seasons = parse_csv_ints(args.recent_seasons)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    baseline = scored_frame(read_csv_table(args.baseline_features), args.prediction_mode)
    target = scored_frame(read_csv_table(args.target_features), args.prediction_mode)

    feature_columns = select_feature_columns(baseline)
    missing_in_target = [c for c in feature_columns if c not in target.columns]
    if missing_in_target:
        raise ValueError(f"Target table missing training feature columns: {missing_in_target[:10]}")

    print(f"feature columns: {len(feature_columns)}")
    print(f"baseline training rows (all seasons): {len(baseline)}")
    print(f"target 2026 scored rows: {len(target)}")

    # Primary evaluation: 2026 season-to-date
    target_results = evaluate_variants(
        baseline, target, feature_columns, recent_seasons, args, eval_label="target_2026_scored"
    )

    # Sanity check: hold out 2025, train on 2021-2024 baseline vs 2024-only challenger
    holdout_2025 = baseline[baseline["season"] == 2025]
    pre_2025 = baseline[baseline["season"] < 2025]
    holdout_results = evaluate_variants(
        pre_2025,
        holdout_2025,
        feature_columns,
        [2024],
        args,
        eval_label="holdout_2025",
    )

    results = pd.concat([target_results, holdout_results], ignore_index=True)
    ordered = ["eval_set", "model", "train_rows", *REPORT_METRICS]
    ordered = [c for c in ordered if c in results.columns]
    results = results[ordered]
    write_csv_table(results, output / "challenger_metrics.csv")

    print("\n=== Recent-season challenger results ===")
    with pd.option_context("display.width", 160, "display.max_columns", 20):
        print(results.to_string(index=False))

    # Markdown summary
    lines = ["# Recent-Season Training Challenger", ""]
    for eval_set in results["eval_set"].unique():
        block = results[results["eval_set"] == eval_set]
        lines.append(f"## {eval_set}")
        lines.append("")
        lines.append("| model | train_rows | n_games | log_loss | brier | accuracy | acc_conf_60 | cov_conf_60 |")
        lines.append("| --- | --- | --- | --- | --- | --- | --- | --- |")
        for _, r in block.iterrows():
            lines.append(
                f"| {r['model']} | {int(r['train_rows'])} | {int(r['n_games'])} | "
                f"{r['log_loss']:.4f} | {r['brier_score']:.4f} | {r['accuracy']:.4f} | "
                f"{r['accuracy_conf_60']:.4f} | {r['coverage_conf_60']:.4f} |"
            )
        lines.append("")
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"\nWrote -> {output / 'challenger_metrics.csv'} and summary.md")


if __name__ == "__main__":
    main()
