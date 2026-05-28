"""Build NPB full-2024 features and run a chronological holdout comparison.

The 50-game smoke established the pipeline; this scales it to the full 858-game
regular season and adds an honest train/test holdout split for model selection.
Batting detail limitation (no 2B/3B/BB/HBP/SF columns) is unchanged - that gap
is per the source investigation and is documented in NPB_FEATURE_GAP.md.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import select_feature_columns
from mlb_winprob.features import FeatureBuilder
from mlb_winprob.models import make_classifier
from mlb_winprob.park_factors import build_empirical_park_factors
from mlb_winprob.schemas import FeatureBuildConfig


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canonical-dir", default="outputs/npb_full/standardized/npb/canonical_2024")
    parser.add_argument("--venues", default="data/standardized/npb/venues_seed.csv")
    parser.add_argument("--output-dir", default="outputs/npb_full")
    parser.add_argument("--models", default="random_forest,random_forest_shallow,random_forest_deep,extra_trees,logistic")
    parser.add_argument("--test-fraction", type=float, default=0.20)
    args = parser.parse_args()

    canonical = Path(args.canonical_dir)
    out = Path(args.output_dir)
    (out / "processed").mkdir(parents=True, exist_ok=True)

    games = read_csv_table(canonical / "games.csv")
    games = games[games["game_type"] == "Reg Season"].copy().reset_index(drop=True)
    print(f"Regular-season games: {len(games)}")
    batting_logs = read_csv_table(canonical / "batting_logs.csv")
    pitcher_logs = read_csv_table(canonical / "pitcher_logs.csv")
    lineups = read_csv_table(canonical / "lineups.csv")
    venues = read_csv_table(args.venues)

    # Empirical park factors (small NPB, so min_games tuned low)
    pf_path = out / "processed" / "park_factors_empirical_npb_2024.csv"
    write_csv_table(
        build_empirical_park_factors([canonical], min_games=20),
        pf_path,
    )

    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        venues=venues,
        park_factors=read_csv_table(pf_path),
    )
    features = features.drop_duplicates("game_id", keep="first").reset_index(drop=True)
    feature_path = out / "processed" / "features_confirmed_npb_2024_full.csv"
    write_csv_table(features, feature_path)
    print(f"features: {len(features)} rows, {features.shape[1]} cols -> {feature_path}")

    features = features.sort_values("game_date").reset_index(drop=True)
    n_test = max(1, int(len(features) * args.test_fraction))
    n_train = len(features) - n_test
    train = features.iloc[:n_train].copy()
    test = features.iloc[n_train:].copy()
    print(f"Chronological split: train {len(train)} (until {train['game_date'].iloc[-1]}) | test {len(test)} (from {test['game_date'].iloc[0]})")

    feature_columns = [c for c in select_feature_columns(train) if c not in {"home_score", "away_score"}]
    print(f"feature_columns selected: {len(feature_columns)}")

    if "home_team_win" in train.columns:
        target = "home_team_win"
    else:
        target = "home_score"
        train[target] = (train["home_score"].astype(int) > train["away_score"].astype(int)).astype(int)
        test[target] = (test["home_score"].astype(int) > test["away_score"].astype(int)).astype(int)
        target = "home_team_win"
        train["home_team_win"] = (train["home_score"].astype(int) > train["away_score"].astype(int)).astype(int)
        test["home_team_win"] = (test["home_score"].astype(int) > test["away_score"].astype(int)).astype(int)

    x_train = train[feature_columns]
    y_train = train["home_team_win"].astype(int)
    x_test = test[feature_columns]
    y_test = test["home_team_win"].astype(int)

    rows = []
    for model_name in [m.strip() for m in args.models.split(",") if m.strip()]:
        try:
            model = make_classifier(model_name, random_state=42)
            model.fit(x_train, y_train)
            proba = model.predict_proba(x_test)[:, 1]
            pred = (proba >= 0.5).astype(int)
            rows.append({
                "model_name": model_name,
                "log_loss": float(log_loss(y_test, np.clip(proba, 1e-6, 1 - 1e-6))),
                "brier_score": float(brier_score_loss(y_test, proba)),
                "accuracy": float(accuracy_score(y_test, pred)),
                "n_test": int(len(test)),
            })
        except Exception as exc:
            print(f"  skip {model_name}: {exc}")

    metrics = pd.DataFrame(rows).sort_values("log_loss").reset_index(drop=True)
    metrics_path = out / "model_test_npb_full_2024.csv"
    write_csv_table(metrics, metrics_path)
    print("\nNPB full-2024 model comparison:")
    print(metrics.to_string(index=False))
    print(f"\nWrote {metrics_path}")


if __name__ == "__main__":
    main()
