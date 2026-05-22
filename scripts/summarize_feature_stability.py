"""Summarize season-to-season stability of feature importance outputs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def load_many(paths: list[Path]) -> pd.DataFrame:
    return pd.concat([pd.read_csv(path) for path in paths], ignore_index=True) if paths else pd.DataFrame()


def summarize_top_stability(frame: pd.DataFrame, *, value_column: str, top_n: int) -> pd.DataFrame:
    top = (
        frame.sort_values(["holdout_season", value_column], ascending=[True, False])
        .groupby("holdout_season")
        .head(top_n)
        .copy()
    )
    top["rank"] = top.groupby("holdout_season")[value_column].rank(method="first", ascending=False)
    return (
        top.groupby("feature", as_index=False)
        .agg(
            top_count=("holdout_season", "nunique"),
            mean_rank=("rank", "mean"),
            mean_value=(value_column, "mean"),
        )
        .sort_values(["top_count", "mean_rank", "mean_value"], ascending=[False, True, False])
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--experiment-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--top-n", type=int, default=20)
    args = parser.parse_args()

    experiment = Path(args.experiment_dir)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)

    feature_importance = load_many(sorted((experiment / "feature_importance").glob("feature_importance_*_random_forest.csv")))
    shap_importance = load_many(sorted((experiment / "shap_importance").glob("shap_importance_*_random_forest.csv")))

    fi_stability = summarize_top_stability(feature_importance, value_column="importance", top_n=args.top_n)
    shap_stability = summarize_top_stability(shap_importance, value_column="mean_abs_shap", top_n=args.top_n)
    fi_stability.to_csv(output / "feature_importance_top_stability.csv", index=False)
    shap_stability.to_csv(output / "shap_top_stability.csv", index=False)

    stable = sorted(
        set(fi_stability.loc[fi_stability["top_count"] >= 3, "feature"]).intersection(
            set(shap_stability.loc[shap_stability["top_count"] >= 3, "feature"])
        )
    )
    watch = sorted(
        set(fi_stability.loc[fi_stability["top_count"] == 1, "feature"]).union(
            set(shap_stability.loc[shap_stability["top_count"] == 1, "feature"])
        )
    )
    pd.DataFrame({"stable_feature": stable}).to_csv(output / "stable_features_intersection.csv", index=False)
    pd.DataFrame({"watch_feature": watch}).to_csv(output / "low_stability_watch_features.csv", index=False)

    lines = [
        "# Feature Stability Summary",
        "",
        f"Source: `{experiment}`",
        "",
        "## Stable Features In Both Feature Importance And SHAP",
        "",
        pd.DataFrame({"stable_feature": stable}).head(40).to_string(index=False),
        "",
        "## Feature Importance Top Stability",
        "",
        fi_stability.head(25).to_string(index=False),
        "",
        "## SHAP Top Stability",
        "",
        shap_stability.head(25).to_string(index=False),
        "",
        "## Readout",
        "",
        "Stable signal is concentrated in team form, run prevention, bullpen FIP/WHIP, and starter K-BB/FIP style features. Low-stability one-off features should be treated as pruning/watchlist candidates only after grouped ablation, not from importance alone.",
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote feature stability summary to {output}")


if __name__ == "__main__":
    main()
