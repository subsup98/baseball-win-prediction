"""Train and score a small chronological NPB smoke model."""

from __future__ import annotations

import argparse
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import select_feature_columns
from mlb_winprob.models import make_classifier


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = ["" if pd.isna(value) else str(value) for value in row.tolist()]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="outputs/npb_smoke/processed/features_confirmed_npb_model_ready_sample_50.csv")
    parser.add_argument("--output-dir", default="outputs/npb_smoke/model_smoke")
    parser.add_argument("--model-name", default="logistic")
    parser.add_argument("--test-rows", type=int, default=10)
    parser.add_argument("--random-state", type=int, default=42)
    args = parser.parse_args()

    features = read_csv_table(args.features).sort_values(["game_date", "game_id"]).reset_index(drop=True)
    if "home_team_win" not in features.columns:
        raise ValueError("features must include home_team_win")
    frame = features.dropna(subset=["home_team_win"]).copy()
    if len(frame) <= args.test_rows:
        raise ValueError("--test-rows must be smaller than the number of scored rows")

    train = frame.iloc[: -args.test_rows].copy()
    test = frame.iloc[-args.test_rows :].copy()
    feature_columns = select_feature_columns(train)
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")

    estimator = make_classifier(args.model_name, random_state=args.random_state)
    estimator.fit(train[feature_columns], train["home_team_win"].astype(int))
    probabilities = estimator.predict_proba(test[feature_columns])[:, 1]
    predictions = test[
        [
            column
            for column in [
                "game_id",
                "game_date",
                "home_team",
                "away_team",
                "home_score",
                "away_score",
                "home_team_win",
            ]
            if column in test.columns
        ]
    ].copy()
    predictions["predicted_home_win_probability"] = probabilities
    predictions["predicted_winner"] = np.where(probabilities >= 0.5, predictions["home_team"], predictions["away_team"])
    predictions["actual_winner"] = np.where(predictions["home_team_win"].astype(int).eq(1), predictions["home_team"], predictions["away_team"])
    predictions["correct"] = predictions["predicted_winner"].eq(predictions["actual_winner"]).astype(int)

    y_true = test["home_team_win"].astype(int)
    metrics = pd.DataFrame(
        [
            {
                "model_name": args.model_name,
                "train_rows": len(train),
                "test_rows": len(test),
                "feature_count": len(feature_columns),
                "accuracy": accuracy_score(y_true, probabilities >= 0.5),
                "brier_score": brier_score_loss(y_true, probabilities),
                "log_loss": log_loss(y_true, probabilities, labels=[0, 1]),
                "home_win_rate_test": float(y_true.mean()),
                "mean_predicted_home_win": float(np.mean(probabilities)),
            }
        ]
    )

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_csv_table(predictions, output / "predictions.csv")
    write_csv_table(metrics, output / "metrics.csv")
    preview = predictions[
        [
            "game_date",
            "away_team",
            "home_team",
            "away_score",
            "home_score",
            "predicted_home_win_probability",
            "predicted_winner",
            "actual_winner",
            "correct",
        ]
    ].copy()
    lines = [
        "# NPB Smoke Model Predictions",
        "",
        "## Metrics",
        "",
        _markdown_table(metrics),
        "",
        "## Predictions",
        "",
        _markdown_table(preview),
        "",
        "This is a smoke check on a small chronological split, not a production-grade NPB model evaluation.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    joblib.dump(
        {
            "model_name": args.model_name,
            "feature_columns": feature_columns,
            "estimator": estimator,
            "training_rows": len(train),
            "training_features": str(args.features),
        },
        output / "model.joblib",
    )

    print(metrics.to_string(index=False))
    print(f"Wrote predictions: {output / 'predictions.csv'}")
    print(f"Wrote summary: {output / 'summary.md'}")
    print(f"Wrote model: {output / 'model.joblib'}")


if __name__ == "__main__":
    main()
