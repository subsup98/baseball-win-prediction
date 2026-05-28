"""Test Recent Form v2 narrow signals as a pick-rule overlay rather than features.

Idea: instead of feeding recent-form columns to the model (which the v2 ablation
showed adds tiny lift), use them as a side-overlay rule:
  - main model = baseline + random_forest (current default)
  - overlay = require home_pythag_diff and home_run_diff_recent agree with the
    main pick before we consider it actionable.

Output: per-confidence-band actionable accuracy with and without overlay agreement.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_oof_win_predictions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True, help="Recent-form-enabled features CSV.")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--main-model", default="random_forest")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--prediction-mode", default="confirmed_lineup")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    seasons = [int(s.strip()) for s in args.holdout_seasons.split(",") if s.strip()]

    oof = run_oof_win_predictions(
        features,
        holdout_seasons=seasons,
        model_names=[args.main_model],
        prediction_mode=args.prediction_mode,
        random_state=args.seed,
    )
    if "home_win_probability" not in oof.columns:
        raise SystemExit("Expected 'home_win_probability' in OOF output; got: " + ", ".join(oof.columns))

    oof["game_id"] = oof["game_id"].astype(str)
    feats = features.copy()
    feats["game_id"] = feats["game_id"].astype(str)
    overlay_cols = [
        f"{side}_team_{stem}"
        for side in ("home", "away")
        for stem in (
            "actual_minus_pythag_last_20",
            "weighted_run_diff_last_10",
            "runs_for_volatility_last_10",
        )
        if f"{side}_team_{stem}" in feats.columns
    ]
    if not overlay_cols:
        raise SystemExit("No recent-form home_/away_ overlay columns found in features.")
    print(f"Overlay sources detected: {overlay_cols}")

    overlay_df = oof.merge(feats[["game_id"] + overlay_cols], on="game_id", how="left")
    overlay_df["pythag_diff"] = (
        overlay_df.get("home_team_actual_minus_pythag_last_20", 0.0).fillna(0)
        - overlay_df.get("away_team_actual_minus_pythag_last_20", 0.0).fillna(0)
    )
    overlay_df["run_diff_recent10"] = (
        overlay_df.get("home_team_weighted_run_diff_last_10", 0.0).fillna(0)
        - overlay_df.get("away_team_weighted_run_diff_last_10", 0.0).fillna(0)
    )
    overlay_df["pick_main"] = np.where(overlay_df["home_win_probability"] >= 0.5, "home", "away")
    overlay_df["confidence_main"] = np.where(
        overlay_df["pick_main"] == "home",
        overlay_df["home_win_probability"],
        1.0 - overlay_df["home_win_probability"],
    )
    # Overlay agreement: both pythag_diff and run_diff_recent10 must agree in sign with main pick.
    def _agree(row) -> bool:
        if row["pick_main"] == "home":
            return (row["pythag_diff"] >= 0) and (row["run_diff_recent10"] >= 0)
        return (row["pythag_diff"] <= 0) and (row["run_diff_recent10"] <= 0)

    overlay_df["overlay_agree"] = overlay_df.apply(_agree, axis=1)
    overlay_df["actual_home_win"] = (overlay_df["home_score"] > overlay_df["away_score"]).astype(int)
    overlay_df["main_correct"] = np.where(
        overlay_df["pick_main"] == "home",
        overlay_df["actual_home_win"],
        1 - overlay_df["actual_home_win"],
    )

    # Confidence bands: 53/55/57/60
    bands = [0.53, 0.55, 0.57, 0.60]
    rows = []
    for band in bands:
        for agree_only in [False, True]:
            sub = overlay_df[overlay_df["confidence_main"] >= band].copy()
            if agree_only:
                sub = sub[sub["overlay_agree"]]
            n = len(sub)
            acc = float(sub["main_correct"].mean()) if n else None
            rows.append(
                {
                    "band": band,
                    "agree_only": agree_only,
                    "n": n,
                    "accuracy": acc,
                    "coverage": float(n / len(overlay_df)),
                }
            )
    summary = pd.DataFrame(rows)
    print("\nOverlay rule summary:")
    print(summary.to_string(index=False))
    write_csv_table(summary, out / "overlay_pick_rule_summary.csv")

    # Per-season
    season_rows = []
    for season, sub in overlay_df.groupby("season", dropna=True):
        for band in bands:
            for agree_only in [False, True]:
                sub2 = sub[sub["confidence_main"] >= band]
                if agree_only:
                    sub2 = sub2[sub2["overlay_agree"]]
                n = len(sub2)
                acc = float(sub2["main_correct"].mean()) if n else None
                season_rows.append(
                    {
                        "season": int(season),
                        "band": band,
                        "agree_only": agree_only,
                        "n": n,
                        "accuracy": acc,
                    }
                )
    season_summary = pd.DataFrame(season_rows)
    write_csv_table(season_summary, out / "overlay_pick_rule_by_season.csv")
    print("\nWrote overlay outputs to", out)


if __name__ == "__main__":
    main()
