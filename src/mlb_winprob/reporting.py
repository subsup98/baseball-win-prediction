"""Dataset quality and experiment reporting helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

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


def write_calibration_plot(table: pd.DataFrame, output: str | Path, *, title: str | None = None) -> Path | None:
    """Write a calibration curve PNG for one model/holdout table.

    Matplotlib is optional for the core package, so callers still get CSV
    outputs even if plotting dependencies are unavailable.
    """

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None

    plot_table = table.dropna(subset=["predicted_home_win_rate", "actual_home_win_rate"]).copy()
    if plot_table.empty:
        return None

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(6, 6), dpi=140)
    ax.plot([0, 1], [0, 1], color="#8a8f98", linestyle="--", linewidth=1, label="Perfect calibration")
    ax.plot(
        plot_table["predicted_home_win_rate"],
        plot_table["actual_home_win_rate"],
        color="#2563eb",
        marker="o",
        linewidth=2,
        label="Model",
    )
    if "n_games" in plot_table.columns:
        sizes = plot_table["n_games"].fillna(0).clip(lower=1)
        ax.scatter(
            plot_table["predicted_home_win_rate"],
            plot_table["actual_home_win_rate"],
            s=20 + 2 * sizes,
            color="#2563eb",
            alpha=0.18,
            edgecolors="none",
        )
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("Predicted home win rate")
    ax.set_ylabel("Actual home win rate")
    ax.set_title(title or "Calibration")
    ax.grid(True, color="#d7dce2", linewidth=0.8, alpha=0.8)
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(target)
    plt.close(fig)
    return target


def feature_importance_table(estimator: object, feature_columns: list[str]) -> pd.DataFrame:
    """Return sorted feature importances for estimators that expose them."""

    model = estimator
    if hasattr(estimator, "named_steps"):
        named_steps = getattr(estimator, "named_steps")
        model = named_steps.get("model", estimator)
    importances = getattr(model, "feature_importances_", None)
    if importances is None:
        return pd.DataFrame()

    values = np.asarray(importances, dtype=float)
    if len(values) != len(feature_columns):
        return pd.DataFrame()
    table = pd.DataFrame({"feature": feature_columns, "importance": values})
    total = table["importance"].sum()
    table["importance_share"] = table["importance"] / total if total > 0 else np.nan
    return table.sort_values(["importance", "feature"], ascending=[False, True]).reset_index(drop=True)


def _pipeline_model_and_matrix(estimator: object, x: pd.DataFrame) -> tuple[Any, np.ndarray]:
    if hasattr(estimator, "named_steps"):
        named_steps = getattr(estimator, "named_steps")
        model = named_steps.get("model", estimator)
        if hasattr(estimator, "steps") and len(getattr(estimator, "steps")) > 1:
            matrix = estimator[:-1].transform(x)
        else:
            matrix = x.to_numpy()
        return model, np.asarray(matrix, dtype=float)
    return estimator, x.to_numpy(dtype=float)


def shap_importance_table(
    estimator: object,
    x: pd.DataFrame,
    feature_columns: list[str],
    *,
    max_rows: int = 250,
    random_state: int = 42,
) -> pd.DataFrame:
    """Return mean absolute Tree SHAP values when optional shap is installed."""

    if x.empty:
        return pd.DataFrame()
    try:
        import shap
    except ImportError:
        return pd.DataFrame()

    sample = x[feature_columns].copy()
    if len(sample) > max_rows:
        sample = sample.sample(max_rows, random_state=random_state)

    model, matrix = _pipeline_model_and_matrix(estimator, sample)
    if not hasattr(model, "feature_importances_"):
        return pd.DataFrame()

    try:
        explainer = shap.TreeExplainer(model)
        shap_values = explainer.shap_values(matrix)
    except Exception:
        return pd.DataFrame()

    if isinstance(shap_values, list):
        values = np.asarray(shap_values[1] if len(shap_values) > 1 else shap_values[0], dtype=float)
    else:
        values = np.asarray(shap_values, dtype=float)
        if values.ndim == 3:
            output_index = 1 if values.shape[2] > 1 else 0
            values = values[:, :, output_index]
    if values.ndim != 2 or values.shape[1] != len(feature_columns):
        return pd.DataFrame()

    table = pd.DataFrame(
        {
            "feature": feature_columns,
            "mean_abs_shap": np.abs(values).mean(axis=0),
            "mean_shap": values.mean(axis=0),
        }
    )
    total = table["mean_abs_shap"].sum()
    table["shap_share"] = table["mean_abs_shap"] / total if total > 0 else np.nan
    return table.sort_values(["mean_abs_shap", "feature"], ascending=[False, True]).reset_index(drop=True)


def write_feature_importance_summary(tables: dict[tuple[int, str], pd.DataFrame], output: str | Path, *, top_n: int = 20) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Feature Importance Report", ""]
    if not tables:
        lines.extend(["_No feature importance tables were available._", ""])
    for (season, model_name), table in sorted(tables.items()):
        lines.extend([f"## {season} {model_name}", ""])
        preview = table.head(top_n).copy()
        preview["importance"] = preview["importance"].map(lambda value: f"{value:.6f}")
        preview["importance_share"] = preview["importance_share"].map(lambda value: f"{value:.4f}")
        lines.extend([_markdown_table(preview), ""])
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


def write_shap_importance_summary(tables: dict[tuple[int, str], pd.DataFrame], output: str | Path, *, top_n: int = 20) -> Path:
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# SHAP Importance Report", ""]
    if not tables:
        lines.extend(["_No SHAP tables were available. Install the optional `explain` extra to enable Tree SHAP output._", ""])
    for (season, model_name), table in sorted(tables.items()):
        lines.extend([f"## {season} {model_name}", ""])
        preview = table.head(top_n).copy()
        preview["mean_abs_shap"] = preview["mean_abs_shap"].map(lambda value: f"{value:.6f}")
        preview["mean_shap"] = preview["mean_shap"].map(lambda value: f"{value:.6f}")
        preview["shap_share"] = preview["shap_share"].map(lambda value: f"{value:.4f}")
        lines.extend([_markdown_table(preview), ""])
    target.write_text("\n".join(lines), encoding="utf-8")
    return target


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
    plot_paths = []
    feature_importance_dir = output / "feature_importance"
    feature_importance_tables: dict[tuple[int, str], pd.DataFrame] = {}
    shap_importance_dir = output / "shap_importance"
    shap_importance_tables: dict[tuple[int, str], pd.DataFrame] = {}
    report_features = features.copy()
    if prediction_mode is not None and "prediction_mode" in report_features.columns:
        report_features = report_features[report_features["prediction_mode"] == prediction_mode].copy()
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
            plot_path = write_calibration_plot(
                table,
                calibration_dir / f"calibration_{season}_{safe_name}.png",
                title=f"{season} {model_name}",
            )
            if plot_path is not None:
                plot_paths.append(plot_path)
        for model_name, estimator in result.fitted_models.items():
            table = feature_importance_table(estimator, result.feature_columns)
            if table.empty:
                continue
            safe_name = model_name.replace("/", "_")
            table.insert(0, "holdout_season", season)
            table.insert(1, "model_name", model_name)
            write_csv_table(table, feature_importance_dir / f"feature_importance_{season}_{safe_name}.csv")
            feature_importance_tables[(season, model_name)] = table
            if "season" in report_features.columns:
                shap_frame = report_features[report_features["season"] == season]
            else:
                shap_frame = report_features
            shap_table = shap_importance_table(estimator, shap_frame, result.feature_columns)
            if shap_table.empty:
                continue
            shap_table.insert(0, "holdout_season", season)
            shap_table.insert(1, "model_name", model_name)
            write_csv_table(shap_table, shap_importance_dir / f"shap_importance_{season}_{safe_name}.csv")
            shap_importance_tables[(season, model_name)] = shap_table

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
    if plot_paths:
        paths["calibration_plots"] = calibration_dir
    if feature_importance_tables:
        paths["feature_importance"] = feature_importance_dir
        write_feature_importance_summary(feature_importance_tables, feature_importance_dir / "summary.md")
    if shap_importance_tables:
        paths["shap_importance"] = shap_importance_dir
        write_shap_importance_summary(shap_importance_tables, shap_importance_dir / "summary.md")
    write_csv_table(all_metrics, paths["metrics"])
    write_csv_table(best_by_season, paths["best"])
    return paths
