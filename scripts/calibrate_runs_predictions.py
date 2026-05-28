"""Post-hoc calibration and quantile-regression dispersion for runs predictions.

Two outputs produced side-by-side with the existing catboost_regressor OOF totals:

  (A) Isotonic + linear post-hoc bias correction
      For each holdout season >= 2023, fit a calibration map on prior holdout seasons'
      (OOF pred_total, actual_total) pairs, then apply to the current season's
      pred_total. Yields a `calibrated_pred_total` column.

  (B) LightGBM quantile regression (p10 / p50 / p90)
      Train one regressor per quantile on training seasons' actual home+away total,
      using the same feature set as the runs catboost. Outputs `quantile_p10/p50/p90`.

Joins both back with the SBR market odds and re-summarizes the OU pick-rule buckets
so we can compare calibrated vs raw vs quantile-median picks against real lines.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LinearRegression

from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import season_holdout_split, select_feature_columns
from mlb_winprob.odds import evaluate_predictions_against_market, summarize_market_ou_rules


def fit_isotonic_calibrator(
    pred: np.ndarray, actual: np.ndarray
) -> tuple[IsotonicRegression, LinearRegression]:
    """Fit an isotonic map plus a residual linear bias correction.

    Isotonic guarantees monotonicity, the linear residual removes any leftover
    systematic shift (e.g. the +0.5 over-bias the diagnostic flagged).
    """
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(pred, actual)
    iso_pred = iso.predict(pred)
    residuals = actual - iso_pred
    linear = LinearRegression()
    linear.fit(iso_pred.reshape(-1, 1), residuals + iso_pred)
    return iso, linear


def apply_calibrator(
    iso: IsotonicRegression, linear: LinearRegression, pred: np.ndarray
) -> np.ndarray:
    iso_pred = iso.predict(pred)
    return linear.predict(iso_pred.reshape(-1, 1))


def fit_quantile_model(x_train, y_train, alpha: float, random_state: int = 42):
    try:
        from lightgbm import LGBMRegressor
    except ImportError as exc:
        raise SystemExit(
            "LightGBM is required for quantile regression. Install with `pip install lightgbm`."
        ) from exc
    model = LGBMRegressor(
        objective="quantile",
        alpha=alpha,
        n_estimators=400,
        learning_rate=0.05,
        max_depth=-1,
        num_leaves=63,
        min_child_samples=40,
        random_state=random_state,
        verbose=-1,
    )
    model.fit(x_train, y_train)
    return model


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", required=True)
    parser.add_argument("--oof-predictions", required=True, help="Existing catboost OOF predictions CSV.")
    parser.add_argument("--odds", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    parser.add_argument("--prediction-mode", default="confirmed_lineup")
    args = parser.parse_args()

    features = read_csv_table(args.features)
    if "prediction_mode" in features.columns:
        features = features[features["prediction_mode"] == args.prediction_mode].copy()
    oof = read_csv_table(args.oof_predictions)
    odds = read_csv_table(args.odds)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    holdout_seasons = [int(s.strip()) for s in args.holdout_seasons.split(",") if s.strip()]
    oof["game_id"] = oof["game_id"].astype(str)

    # ----- (A) Isotonic calibration --------------------------------------------------
    iso_rows: list[pd.DataFrame] = []
    for i, season in enumerate(holdout_seasons):
        season_pred = oof[oof["holdout_season"] == season].copy()
        season_pred["calibrated_pred_total"] = season_pred["pred_total"].astype(float)
        if i == 0:
            print(f"  {season}: no prior OOF -> calibration skipped, raw pred kept.")
        else:
            prior = oof[oof["holdout_season"].isin(holdout_seasons[:i])].dropna(
                subset=["pred_total", "actual_total"]
            )
            iso, linear = fit_isotonic_calibrator(
                prior["pred_total"].to_numpy(),
                prior["actual_total"].to_numpy(),
            )
            calibrated = apply_calibrator(iso, linear, season_pred["pred_total"].to_numpy())
            season_pred["calibrated_pred_total"] = calibrated
            mae_raw = float((season_pred["pred_total"] - season_pred["actual_total"]).abs().mean())
            mae_cal = float((season_pred["calibrated_pred_total"] - season_pred["actual_total"]).abs().mean())
            bias_raw = float((season_pred["pred_total"] - season_pred["actual_total"]).mean())
            bias_cal = float((season_pred["calibrated_pred_total"] - season_pred["actual_total"]).mean())
            print(
                f"  {season}: cal fit on {len(prior)} prior rows | "
                f"raw MAE {mae_raw:.3f} bias {bias_raw:+.3f}  ->  "
                f"cal MAE {mae_cal:.3f} bias {bias_cal:+.3f}"
            )
        iso_rows.append(season_pred)
    calibrated_pred = pd.concat(iso_rows, ignore_index=True)

    # ----- (B) Quantile regression p10/p50/p90 --------------------------------------
    print("\nQuantile regression (lightgbm) ...")
    quantile_rows: list[pd.DataFrame] = []
    quantiles = [0.10, 0.50, 0.90]
    for season in holdout_seasons:
        train, test = season_holdout_split(features, holdout_season=season)
        if train.empty or test.empty:
            print(f"  Skipped {season}: train={len(train)} test={len(test)}")
            continue
        feature_columns = [
            c for c in select_feature_columns(train) if c not in {"home_score", "away_score"}
        ]
        x_train = train[feature_columns]
        x_test = test[feature_columns]
        y_train = (train["home_score"].astype(float) + train["away_score"].astype(float))
        season_test = test[[c for c in ["game_id", "game_date", "home_team", "away_team", "home_score", "away_score", "season"] if c in test.columns]].copy()
        season_test["holdout_season"] = season
        season_test["actual_total"] = season_test["home_score"].astype(float) + season_test["away_score"].astype(float)
        for q in quantiles:
            model = fit_quantile_model(x_train, y_train, alpha=q)
            preds = model.predict(x_test)
            season_test[f"quantile_p{int(q*100):02d}"] = preds
        quantile_rows.append(season_test)
        coverage = ((season_test["actual_total"] >= season_test["quantile_p10"]) & (season_test["actual_total"] <= season_test["quantile_p90"])).mean()
        width = (season_test["quantile_p90"] - season_test["quantile_p10"]).mean()
        median_mae = (season_test["quantile_p50"] - season_test["actual_total"]).abs().mean()
        median_bias = (season_test["quantile_p50"] - season_test["actual_total"]).mean()
        print(f"  {season}: 80% PI coverage {coverage:.3f} | mean width {width:.2f} | p50 MAE {median_mae:.3f} bias {median_bias:+.3f}")
    quantile_pred = pd.concat(quantile_rows, ignore_index=True)
    quantile_pred["game_id"] = quantile_pred["game_id"].astype(str)

    # ----- Merge calibrated + quantile into one wide table --------------------------
    merged = calibrated_pred.merge(
        quantile_pred[["game_id", "quantile_p10", "quantile_p50", "quantile_p90"]],
        on="game_id",
        how="left",
    )
    merged["quantile_pi_width"] = merged["quantile_p90"] - merged["quantile_p10"]
    write_csv_table(merged, out / "predictions_calibrated_quantile.csv")

    # ----- Evaluate each variant against real market lines --------------------------
    def variant_eval(variant_name: str, total_col: str) -> pd.DataFrame:
        view = merged.copy()
        view["pred_total"] = view[total_col]
        ev = evaluate_predictions_against_market(view, odds, lean_margin=0.5, strong_margin=1.5)
        summary = summarize_market_ou_rules(ev)
        summary.insert(0, "variant", variant_name)
        return summary, ev

    rule_frames: list[pd.DataFrame] = []
    season_rule_frames: list[pd.DataFrame] = []
    eval_rows = []
    for variant_name, col in [
        ("raw_pred_total", "pred_total"),
        ("calibrated_pred_total", "calibrated_pred_total"),
        ("quantile_p50", "quantile_p50"),
    ]:
        if col not in merged.columns:
            continue
        summary, ev = variant_eval(variant_name, col)
        rule_frames.append(summary)
        eval_rows.append((variant_name, ev))
        # per-season
        for season, sub in ev.groupby("holdout_season", dropna=True):
            s = summarize_market_ou_rules(sub)
            s.insert(0, "variant", variant_name)
            s["holdout_season"] = int(season)
            season_rule_frames.append(s)

    rule_summary = pd.concat(rule_frames, ignore_index=True)
    season_rule_summary = pd.concat(season_rule_frames, ignore_index=True)
    write_csv_table(rule_summary, out / "ou_pick_rule_summary_by_variant.csv")
    write_csv_table(season_rule_summary, out / "ou_pick_rule_summary_by_variant_season.csv")

    print("\nOU pick-rule summary by variant (all seasons, real market lines):")
    print(rule_summary.to_string(index=False))

    # ----- Dispersion table ---------------------------------------------------------
    disp_rows = []
    for variant_name, col in [("raw_pred_total", "pred_total"), ("calibrated_pred_total", "calibrated_pred_total"), ("quantile_p50", "quantile_p50")]:
        if col not in merged.columns:
            continue
        sub = merged.dropna(subset=[col, "actual_total"])
        diff_actual = sub[col] - sub["actual_total"]
        disp_rows.append(
            {
                "variant": variant_name,
                "n": int(len(sub)),
                "pred_std": float(sub[col].std()),
                "bias_vs_actual": float(diff_actual.mean()),
                "mae_vs_actual": float(diff_actual.abs().mean()),
                "rmse_vs_actual": float(np.sqrt((diff_actual ** 2).mean())),
            }
        )
    disp = pd.DataFrame(disp_rows)
    write_csv_table(disp, out / "dispersion_by_variant.csv")
    print("\nDispersion by variant:")
    print(disp.to_string(index=False))

    print(f"\nWrote calibration outputs to {out}")


if __name__ == "__main__":
    main()
