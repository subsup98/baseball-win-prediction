"""Evaluate runs-model OOF predictions against real historical market totals.

Replaces the synthetic 8.5 line with each game's median closing total across SBR books.
Outputs:
  - per-game CSV with market line + ou pick + correctness
  - pick-rule summary (pass/lean/strong) on scored, non-pass rows
  - calibration table: predicted total bucket -> mean market line, mean actual total
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.odds import evaluate_predictions_against_market, summarize_market_ou_rules


def calibration_table(joined: pd.DataFrame) -> pd.DataFrame:
    df = joined.dropna(subset=["pred_total", "market_line", "actual_total"]).copy()
    if df.empty:
        return pd.DataFrame()
    df["pred_bucket"] = pd.cut(df["pred_total"], bins=[0, 7, 7.5, 8, 8.5, 9, 9.5, 10, 20])
    grp = df.groupby("pred_bucket", observed=True).agg(
        n=("pred_total", "size"),
        mean_pred=("pred_total", "mean"),
        mean_market=("market_line", "mean"),
        mean_actual=("actual_total", "mean"),
        actual_over_rate=("actual_total", lambda s: float((s > df.loc[s.index, "market_line"]).mean())),
    )
    grp["pred_minus_market"] = grp["mean_pred"] - grp["mean_market"]
    grp["pred_minus_actual"] = grp["mean_pred"] - grp["mean_actual"]
    return grp.reset_index()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--predictions", required=True)
    parser.add_argument("--odds", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--lean-margin", type=float, default=0.5)
    parser.add_argument("--strong-margin", type=float, default=1.5)
    args = parser.parse_args()

    predictions = read_csv_table(args.predictions)
    odds = read_csv_table(args.odds)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    evaluated = evaluate_predictions_against_market(
        predictions,
        odds,
        lean_margin=args.lean_margin,
        strong_margin=args.strong_margin,
    )
    write_csv_table(evaluated, out / "predictions_with_market_line.csv")

    matched = evaluated.dropna(subset=["market_line"])
    print(f"Predictions: {len(predictions)} | with market line: {len(matched)} ({len(matched)/max(1,len(predictions)):.1%})")

    rule_summary = summarize_market_ou_rules(evaluated)
    write_csv_table(rule_summary, out / "ou_pick_rule_summary.csv")
    print("\nOU pick-rule summary (market line, all 2022-2025 OOF):")
    print(rule_summary.to_string(index=False))

    by_season = []
    for season, sub in evaluated.groupby("holdout_season", dropna=True):
        s = summarize_market_ou_rules(sub)
        s["holdout_season"] = int(season)
        by_season.append(s)
    if by_season:
        per_season = pd.concat(by_season, ignore_index=True)
        write_csv_table(per_season, out / "ou_pick_rule_summary_by_season.csv")
        print("\nOU pick-rule summary by season:")
        print(per_season.to_string(index=False))

    calib = calibration_table(evaluated)
    write_csv_table(calib, out / "calibration_pred_vs_market.csv")
    print("\nCalibration (pred_total bucket vs market line / actual):")
    print(calib.to_string(index=False))

    # Overall dispersion: how much our predicted total varies vs market
    valid = evaluated.dropna(subset=["pred_total", "market_line", "actual_total"])
    if not valid.empty:
        diff = valid["pred_total"] - valid["market_line"]
        actual_minus_market = valid["actual_total"] - valid["market_line"]
        dispersion = pd.DataFrame(
            [
                {
                    "metric": "pred_total_std",
                    "value": float(valid["pred_total"].std()),
                },
                {
                    "metric": "market_line_std",
                    "value": float(valid["market_line"].std()),
                },
                {
                    "metric": "actual_total_std",
                    "value": float(valid["actual_total"].std()),
                },
                {
                    "metric": "pred_minus_market_mean",
                    "value": float(diff.mean()),
                },
                {
                    "metric": "pred_minus_market_std",
                    "value": float(diff.std()),
                },
                {
                    "metric": "pred_minus_market_mae",
                    "value": float(diff.abs().mean()),
                },
                {
                    "metric": "actual_minus_market_mean",
                    "value": float(actual_minus_market.mean()),
                },
                {
                    "metric": "actual_minus_market_mae",
                    "value": float(actual_minus_market.abs().mean()),
                },
                {
                    "metric": "n_scored",
                    "value": float(len(valid)),
                },
            ]
        )
        write_csv_table(dispersion, out / "dispersion_metrics.csv")
        print("\nDispersion metrics:")
        print(dispersion.to_string(index=False))

    print(f"\nWrote market-OU evaluation to {out}")


if __name__ == "__main__":
    main()
