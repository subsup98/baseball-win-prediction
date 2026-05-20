"""Dataset quality and experiment reporting helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.constants import TARGET_COLUMN
from mlb_winprob.data_sources import read_csv_table, write_csv_table
from mlb_winprob.experiments import run_model_experiments


ROLLING_MARKERS = (
    "season_to_date",
    "last_",
    "recent_",
    "rest_days",
    "fatigue",
    "used_yesterday",
)


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


def read_feature_tables(paths: list[str | Path]) -> pd.DataFrame:
    frames = []
    for path in paths:
        frame = read_csv_table(path)
        frame["source_file"] = Path(path).name
        frames.append(frame)
    if not frames:
        raise ValueError("At least one feature file is required.")
    return pd.concat(frames, ignore_index=True)


def feature_quality_tables(features: pd.DataFrame) -> dict[str, pd.DataFrame]:
    frame = features.copy()
    if "game_date" in frame.columns:
        frame["game_date"] = pd.to_datetime(frame["game_date"], errors="coerce")

    null_rows = []
    for column in frame.columns:
        series = frame[column]
        row = {
            "column": column,
            "dtype": str(series.dtype),
            "rows": int(len(series)),
            "non_null": int(series.notna().sum()),
            "nulls": int(series.isna().sum()),
            "null_rate": float(series.isna().mean()),
        }
        if pd.api.types.is_numeric_dtype(series):
            numeric = pd.to_numeric(series, errors="coerce")
            row.update(
                {
                    "zero_rate": float((numeric == 0).mean()),
                    "min": float(numeric.min()) if numeric.notna().any() else np.nan,
                    "median": float(numeric.median()) if numeric.notna().any() else np.nan,
                    "max": float(numeric.max()) if numeric.notna().any() else np.nan,
                }
            )
        null_rows.append(row)

    null_rates = pd.DataFrame(null_rows).sort_values(["null_rate", "column"], ascending=[False, True])

    season_summary = (
        frame.groupby("season", dropna=False)
        .agg(
            rows=("game_id", "size"),
            first_game_date=("game_date", "min"),
            last_game_date=("game_date", "max"),
            home_win_rate=(TARGET_COLUMN, "mean") if TARGET_COLUMN in frame.columns else ("game_id", "size"),
        )
        .reset_index()
    )

    rolling_columns = [
        column
        for column in frame.select_dtypes(include=["number", "bool"]).columns
        if any(marker in column for marker in ROLLING_MARKERS)
    ]
    rolling_rows = []
    for season, season_frame in frame.sort_values(["game_date", "game_id"]).groupby("season", dropna=False):
        mature = season_frame[season_frame["game_date"].dt.month >= 5] if "game_date" in season_frame.columns else season_frame
        for column in rolling_columns:
            rolling_rows.append(
                {
                    "season": season,
                    "column": column,
                    "rows": int(len(season_frame)),
                    "null_rate_all": float(season_frame[column].isna().mean()),
                    "null_rate_may_onward": float(mature[column].isna().mean()) if not mature.empty else np.nan,
                    "non_null_may_onward": int(mature[column].notna().sum()) if not mature.empty else 0,
                }
            )
    rolling_readiness = pd.DataFrame(rolling_rows).sort_values(["null_rate_may_onward", "column"], ascending=[False, True])

    return {
        "null_rates": null_rates,
        "season_summary": season_summary,
        "rolling_readiness": rolling_readiness,
    }


def write_feature_quality_report(features: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    tables = feature_quality_tables(features)
    paths = {
        "null_rates": output / "feature_null_rates.csv",
        "season_summary": output / "season_summary.csv",
        "rolling_readiness": output / "rolling_feature_readiness.csv",
        "summary": output / "summary.md",
    }
    for name, table in tables.items():
        write_csv_table(table, paths[name])

    worst_columns = tables["null_rates"].head(12)[["column", "null_rate"]]
    rolling_worst = tables["rolling_readiness"].head(12)[["season", "column", "null_rate_may_onward"]]
    lines = [
        "# Feature Quality Report",
        "",
        f"Rows: {len(features)}",
        f"Columns: {features.shape[1]}",
        "",
        "## Seasons",
        "",
        _markdown_table(tables["season_summary"]),
        "",
        "## Highest Null Rates",
        "",
        _markdown_table(worst_columns),
        "",
        "## Rolling Feature Readiness",
        "",
        _markdown_table(rolling_worst),
        "",
    ]
    paths["summary"].write_text("\n".join(lines), encoding="utf-8")
    return paths


def write_season_holdout_report(
    features: pd.DataFrame,
    output_dir: str | Path,
    *,
    holdout_seasons: list[int],
    model_names: list[str],
    prediction_mode: str | None = None,
) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    metrics_frames = []
    calibration_dir = output / "calibration"
    calibration_dir.mkdir(parents=True, exist_ok=True)
    for season in holdout_seasons:
        result = run_model_experiments(
            features,
            model_names=model_names,
            holdout_season=season,
            prediction_mode=prediction_mode,
        )
        metrics = result.metrics.copy()
        metrics.insert(0, "holdout_season", season)
        metrics_frames.append(metrics)
        for model_name, table in result.calibration.items():
            safe_name = model_name.replace("/", "_")
            write_csv_table(table, calibration_dir / f"calibration_{season}_{safe_name}.csv")

    all_metrics = pd.concat(metrics_frames, ignore_index=True) if metrics_frames else pd.DataFrame()
    best_by_season = (
        all_metrics.sort_values(["holdout_season", "log_loss", "brier_score"])
        .groupby("holdout_season", as_index=False)
        .head(1)
        .reset_index(drop=True)
        if not all_metrics.empty
        else pd.DataFrame()
    )

    paths = {
        "metrics": output / "metrics_by_holdout.csv",
        "best": output / "best_by_holdout.csv",
    }
    write_csv_table(all_metrics, paths["metrics"])
    write_csv_table(best_by_season, paths["best"])
    return paths
