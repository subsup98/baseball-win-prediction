"""Generate per-game OOF runs predictions for 2022-2025 holdouts.

Trains the adopted catboost_regressor (or any other registered runs model) on the
non-holdout seasons and predicts on each held-out season. Output is a per-game CSV
with predicted home/away score + total + run diff, ready to be joined against
historical market odds for OU pick-rule evaluation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import make_regressor, season_holdout_split, select_feature_columns


def parse_csv_ints(value: str) -> list[int]:
    return [int(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--model-name", default="catboost_regressor")
    parser.add_argument("--random-state", type=int, default=42)
    parser.add_argument("--prediction-mode", default="confirmed_lineup")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    if "prediction_mode" in features.columns:
        features = features[features["prediction_mode"] == args.prediction_mode].copy()
    holdout_seasons = parse_csv_ints(args.holdout_seasons)

    output_rows: list[pd.DataFrame] = []
    for season in holdout_seasons:
        train, test = season_holdout_split(features, holdout_season=season)
        if train.empty or test.empty:
            print(f"  Skipped {season}: train={len(train)} test={len(test)}")
            continue
        feature_columns = [
            c
            for c in select_feature_columns(train)
            if c not in {"home_score", "away_score"}
        ]
        x_train = train[feature_columns]
        x_test = test[feature_columns]
        home_model = make_regressor(args.model_name, random_state=args.random_state)
        away_model = make_regressor(args.model_name, random_state=args.random_state + 1)
        home_model.fit(x_train, train["home_score"].astype(float))
        away_model.fit(x_train, train["away_score"].astype(float))
        pred_home = np.clip(home_model.predict(x_test), 0, None)
        pred_away = np.clip(away_model.predict(x_test), 0, None)
        preds = test[[c for c in ["game_id", "game_date", "home_team", "away_team", "home_score", "away_score", "season"] if c in test.columns]].copy()
        preds["model_name"] = args.model_name
        preds["holdout_season"] = season
        preds["pred_home_score"] = pred_home
        preds["pred_away_score"] = pred_away
        preds["pred_total"] = pred_home + pred_away
        preds["pred_run_diff"] = pred_home - pred_away
        preds["actual_total"] = preds["home_score"].astype(float) + preds["away_score"].astype(float)
        output_rows.append(preds)
        print(f"  {season}: train {len(train)} -> test {len(test)} predictions")

    if not output_rows:
        raise SystemExit("No holdout predictions generated.")
    combined = pd.concat(output_rows, ignore_index=True)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    write_csv_table(combined, args.output)
    print(f"Wrote {len(combined)} OOF runs predictions to {args.output}")


if __name__ == "__main__":
    main()
