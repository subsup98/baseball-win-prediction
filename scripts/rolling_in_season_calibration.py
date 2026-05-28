"""In-season rolling bias correction for runs predictions.

Walk through each holdout season chronologically. At each game, compute the
rolling mean residual (pred_total - actual_total) of the most recent N completed
games (no future leakage), then subtract it from the current prediction.

This adapts to regime shifts that cross-season calibration cannot (e.g. 2023
pitch-clock scoring jump).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.odds import evaluate_predictions_against_market, summarize_market_ou_rules


def apply_rolling_calibration(season_df: pd.DataFrame, *, window: int, warmup: int) -> pd.DataFrame:
    """Sort chronologically, then for each game adjust by mean residual of prior N games."""
    df = season_df.sort_values("game_date").reset_index(drop=True).copy()
    residuals = (df["pred_total"] - df["actual_total"]).to_numpy()
    adjustments = np.zeros(len(df))
    for i in range(len(df)):
        if i < warmup:
            adjustments[i] = 0.0
            continue
        start = max(0, i - window)
        recent = residuals[start:i]
        adjustments[i] = float(np.nanmean(recent))
    df["rolling_bias_adjustment"] = adjustments
    df["rolling_calibrated_pred_total"] = df["pred_total"] - df["rolling_bias_adjustment"]
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--oof-predictions", required=True)
    parser.add_argument("--odds", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--window", type=int, default=200)
    parser.add_argument("--warmup", type=int, default=100)
    args = parser.parse_args()

    oof = read_csv_table(args.oof_predictions)
    oof["game_id"] = oof["game_id"].astype(str)
    odds = read_csv_table(args.odds)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    calibrated_seasons: list[pd.DataFrame] = []
    for season, sub in oof.groupby("holdout_season", dropna=True):
        calibrated = apply_rolling_calibration(sub, window=args.window, warmup=args.warmup)
        mae_raw = (calibrated["pred_total"] - calibrated["actual_total"]).abs().mean()
        mae_cal = (calibrated["rolling_calibrated_pred_total"] - calibrated["actual_total"]).abs().mean()
        bias_raw = (calibrated["pred_total"] - calibrated["actual_total"]).mean()
        bias_cal = (calibrated["rolling_calibrated_pred_total"] - calibrated["actual_total"]).mean()
        print(
            f"  {int(season)} | raw MAE {mae_raw:.3f} bias {bias_raw:+.3f}  -> "
            f"rolling MAE {mae_cal:.3f} bias {bias_cal:+.3f}  (window={args.window}, warmup={args.warmup})"
        )
        calibrated_seasons.append(calibrated)
    out_df = pd.concat(calibrated_seasons, ignore_index=True)
    write_csv_table(out_df, out / "predictions_rolling_calibrated.csv")

    # Evaluate
    print("\nOU pick-rule (real market lines) - raw vs rolling-calibrated:")
    rule_frames = []
    for variant_name, col in [("raw_pred_total", "pred_total"), ("rolling_calibrated", "rolling_calibrated_pred_total")]:
        view = out_df.copy()
        view["pred_total"] = view[col]
        ev = evaluate_predictions_against_market(view, odds)
        summary = summarize_market_ou_rules(ev)
        summary.insert(0, "variant", variant_name)
        rule_frames.append(summary)
    rule = pd.concat(rule_frames, ignore_index=True)
    print(rule.to_string(index=False))
    write_csv_table(rule, out / "ou_pick_rule_summary.csv")

    print(f"\nWrote rolling calibration to {out}")


if __name__ == "__main__":
    main()
