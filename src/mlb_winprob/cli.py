"""Command line entrypoints."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import sleep
from zoneinfo import ZoneInfo

import joblib
import numpy as np
import pandas as pd

from mlb_winprob.data_sources import (
    BallDontLieMLBCollector,
    ChadwickRegisterCollector,
    LahmanCollector,
    MLBStatsApiCollector,
    MyKBOStatsCollector,
    OpenMeteoArchiveCollector,
    PyBaseballCollector,
    RetrosheetCollector,
    default_collection_workers,
    download_url,
    read_csv_table,
    write_csv_table,
)
from mlb_winprob.config import config_digest, load_season_holdout_config, versioned_output_dir, write_run_metadata
from mlb_winprob.experiments import make_regressor, run_model_experiments, run_oof_win_predictions, select_feature_columns
from mlb_winprob.evaluation import apply_model_agreement_pick_rules, apply_win_pick_rules, summarize_win_pick_rules
from mlb_winprob.features import FeatureBuilder
from mlb_winprob.id_map import build_external_game_id_map, build_external_player_id_map, write_id_map
from mlb_winprob.kbo import standardize_mykbo_game_tables, standardize_mykbo_schedule_links, standardize_mykbo_tables
from mlb_winprob.models import make_classifier
from mlb_winprob.park_factors import build_empirical_park_factors
from mlb_winprob.prediction import build_prediction_result, simple_key_reasons
from mlb_winprob.reporting import (
    read_feature_tables,
    write_expected_runs_holdout_report,
    write_feature_quality_report,
    write_season_holdout_report,
)
from mlb_winprob.retrosheet import standardize_retrosheet_tables
from mlb_winprob.schemas import FeatureBuildConfig
from mlb_winprob.standardize import (
    manual_lineup_template,
    market_lines_template,
    standardize_manual_lineups,
    standardize_mlb_stats_api_boxscores,
)
from mlb_winprob.statcast import aggregate_statcast_batting, aggregate_statcast_pitching, merge_statcast_quality
from mlb_winprob.weather import augment_weather_with_open_meteo


def _add_common_raw_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--games", required=True)
    parser.add_argument("--batting-logs", required=True)
    parser.add_argument("--pitcher-logs", required=True)
    parser.add_argument("--lineups", required=True)
    parser.add_argument("--weather")
    parser.add_argument("--park-factors")
    parser.add_argument("--venues")
    parser.add_argument("--market-lines", help="Optional CSV with game_id plus total line, odds, movement, and starter change fields.")


def build_features_command(args: argparse.Namespace) -> None:
    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode=args.prediction_mode))
    features = builder.build(
        games=read_csv_table(args.games),
        batting_logs=read_csv_table(args.batting_logs),
        pitcher_logs=read_csv_table(args.pitcher_logs),
        lineups=read_csv_table(args.lineups),
        weather=read_csv_table(args.weather) if args.weather else None,
        park_factors=read_csv_table(args.park_factors) if args.park_factors else None,
        venues=read_csv_table(args.venues) if args.venues else None,
        market_lines=read_csv_table(args.market_lines) if args.market_lines else None,
    )
    write_csv_table(features, args.output)
    print(f"Wrote {len(features)} feature rows to {args.output}")


def combine_features_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.inputs)
    write_csv_table(features, args.output)
    print(f"Wrote {len(features)} combined feature rows to {args.output}")


def _markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row.tolist()) + " |")
    return "\n".join(lines)


def _scored_prediction_rows(predictions: pd.DataFrame, *, actual_winner_column: str = "actual_winner") -> pd.DataFrame:
    if {"home_score", "away_score"}.issubset(predictions.columns):
        home_scores = pd.to_numeric(predictions["home_score"], errors="coerce")
        away_scores = pd.to_numeric(predictions["away_score"], errors="coerce")
        return predictions[home_scores.notna() & away_scores.notna()].copy()
    if actual_winner_column in predictions.columns:
        winners = predictions[actual_winner_column]
        return predictions[winners.notna() & winners.astype(str).str.strip().ne("")].copy()
    return predictions.copy()


TEAM_KO_NAMES = {
    "ARI": "애리조나",
    "AZ": "애리조나",
    "ATL": "애틀랜타",
    "BAL": "볼티모어",
    "BOS": "보스턴",
    "CHC": "컵스",
    "CIN": "신시내티",
    "CLE": "클리블랜드",
    "COL": "콜로라도",
    "CWS": "화이트삭스",
    "DET": "디트로이트",
    "HOU": "휴스턴",
    "KC": "캔자스시티",
    "LAA": "에인절스",
    "LAD": "다저스",
    "MIA": "마이애미",
    "MIL": "밀워키",
    "MIN": "미네소타",
    "NYM": "메츠",
    "NYY": "양키스",
    "ATH": "애슬레틱스",
    "OAK": "애슬레틱스",
    "PHI": "필라델피아",
    "PIT": "피츠버그",
    "SD": "샌디에이고",
    "SEA": "시애틀",
    "SF": "샌프란시스코",
    "STL": "세인트루이스",
    "TB": "탬파베이",
    "TEX": "텍사스",
    "TOR": "토론토",
    "WSH": "워싱턴",
}


def kst_date_to_mlb_date(date_kst: str) -> str:
    return (datetime.fromisoformat(date_kst).date() - timedelta(days=1)).isoformat()


def _team_display(team: object, *, korean: bool = True) -> str:
    value = str(team)
    return TEAM_KO_NAMES.get(value, value) if korean else value


def _prediction_recommendation(confidence: float, *, lean_threshold: float = 0.55, strong_threshold: float = 0.60) -> str:
    if confidence >= strong_threshold:
        return "strong"
    if confidence >= lean_threshold:
        return "lean"
    return "pass"


def _winner_score_text(row: pd.Series, *, korean: bool = True) -> str:
    home = str(row["home_team"])
    away = str(row["away_team"])
    pick = str(row["win_pick"])
    pred_home = int(round(float(row["pred_home_score"])))
    pred_away = int(round(float(row["pred_away_score"])))
    if pick == home and pred_home <= pred_away:
        pred_home = pred_away + 1
    if pick == away and pred_away <= pred_home:
        pred_away = pred_home + 1
    if pick == home:
        return f"{_team_display(pick, korean=korean)} {pred_home}:{pred_away} 승"
    return f"{_team_display(pick, korean=korean)} {pred_away}:{pred_home} 승"


def _readable_prediction_table(
    predictions: pd.DataFrame,
    *,
    schedule: pd.DataFrame | None = None,
    korean: bool = True,
    lean_threshold: float = 0.55,
    strong_threshold: float = 0.60,
) -> pd.DataFrame:
    frame = predictions.copy()
    if schedule is not None and "game_id" in schedule.columns:
        status_columns = [
            column
            for column in ["game_id", "status", "detailed_status", "home_sp_name", "away_sp_name"]
            if column in schedule.columns
        ]
        frame = frame.merge(schedule[status_columns], on="game_id", how="left")
    frame["kst_time"] = pd.to_datetime(frame["game_date"], utc=True, errors="coerce").dt.tz_convert("Asia/Seoul").dt.strftime("%m-%d %H:%M")
    frame["matchup"] = frame.apply(
        lambda row: f"{_team_display(row['away_team'], korean=korean)} @ {_team_display(row['home_team'], korean=korean)}",
        axis=1,
    )
    frame["pick_confidence"] = np.where(
        frame["win_pick"].astype(str).eq(frame["home_team"].astype(str)),
        pd.to_numeric(frame["home_win_probability"], errors="coerce"),
        pd.to_numeric(frame["away_win_probability"], errors="coerce"),
    )
    frame["recommendation"] = frame["pick_confidence"].map(
        lambda value: _prediction_recommendation(float(value), lean_threshold=lean_threshold, strong_threshold=strong_threshold)
        if pd.notna(value)
        else "pass"
    )
    frame["score_prediction"] = frame.apply(lambda row: _winner_score_text(row, korean=korean), axis=1)
    columns = [
        "game_id",
        "kst_time",
        "matchup",
        "status",
        "score_prediction",
        "recommendation",
        "pick_confidence",
        "pred_home_score",
        "pred_away_score",
        "home_sp_name",
        "away_sp_name",
    ]
    return frame[[column for column in columns if column in frame.columns]].sort_values(["kst_time", "game_id"]).reset_index(drop=True)


def feature_quality_report_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.features)
    paths = write_feature_quality_report(features, args.output_dir)
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def season_holdout_report_command(args: argparse.Namespace) -> None:
    config = load_season_holdout_config(args.config) if args.config else None
    feature_paths = config.features if config else args.features
    if not feature_paths:
        raise ValueError("--features is required when --config is not provided.")
    output_dir = args.output_dir or (config.output_dir if config else None)
    if output_dir is None:
        raise ValueError("--output-dir is required when --config is not provided.")
    model_values = config.models if config else [value.strip() for value in args.models.split(",") if value.strip()]
    holdout_values = config.holdout_seasons if config else [int(value.strip()) for value in args.holdout_seasons.split(",") if value.strip()]
    prediction_mode = args.prediction_mode or (config.prediction_mode if config else "confirmed_lineup")
    if config and config.versioned_output:
        output_dir = versioned_output_dir(output_dir, run_name=config.name, digest=config_digest(config))

    features = read_feature_tables(feature_paths)
    paths = write_season_holdout_report(
        features,
        output_dir,
        holdout_seasons=holdout_values,
        model_names=model_values,
        prediction_mode=prediction_mode,
    )
    paths.update(
        write_run_metadata(
            output_dir,
            config=config,
            config_path=args.config,
            feature_paths=feature_paths,
            row_count=len(features),
            column_count=features.shape[1],
        )
    )
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def expected_runs_report_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.features)
    model_values = [value.strip() for value in args.models.split(",") if value.strip()]
    holdout_values = [int(value.strip()) for value in args.holdout_seasons.split(",") if value.strip()]
    synthetic_total_lines = [float(value.strip()) for value in args.synthetic_total_lines.split(",") if value.strip()]
    paths = write_expected_runs_holdout_report(
        features,
        args.output_dir,
        holdout_seasons=holdout_values,
        model_names=model_values,
        prediction_mode=args.prediction_mode,
        synthetic_total_lines=synthetic_total_lines,
    )
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def build_empirical_park_factors_command(args: argparse.Namespace) -> None:
    park_factors = build_empirical_park_factors(
        args.standardized_dirs,
        lag_seasons=args.lag_seasons,
        min_games=args.min_games,
    )
    write_csv_table(park_factors, args.output)
    print(f"Wrote {len(park_factors)} empirical park factor rows to {args.output}")


def train_command(args: argparse.Namespace) -> None:
    features = read_csv_table(args.features)
    model_names = args.models.split(",") if args.models else None
    result = run_model_experiments(
        features,
        model_names=model_names,
        holdout_season=args.holdout_season,
        prediction_mode=args.prediction_mode,
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    result.metrics.to_csv(output_dir / "metrics.csv", index=False)
    for model_name, table in result.calibration.items():
        table.to_csv(output_dir / f"calibration_{model_name}.csv", index=False)
    if result.fitted_models:
        best_name = result.best_model_name
        joblib.dump(
            {
                "model_name": best_name,
                "feature_columns": result.feature_columns,
                "estimator": result.fitted_models[best_name],
            },
            output_dir / "best_model.joblib",
        )
        print(result.metrics.to_string(index=False))
        print(f"Best model: {best_name}")
    else:
        print("No models were trained. Optional booster dependencies may be missing.")


def fit_final_model_command(args: argparse.Namespace) -> None:
    features = read_csv_table(args.features)
    if args.prediction_mode and "prediction_mode" in features.columns:
        features = features[features["prediction_mode"] == args.prediction_mode].copy()
    if "home_team_win" not in features.columns:
        raise ValueError("features must include home_team_win")
    feature_columns = select_feature_columns(features)
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")
    train_frame = features.dropna(subset=["home_team_win"]).copy()
    estimator = make_classifier(args.model_name, random_state=args.random_state)
    estimator.fit(train_frame[feature_columns], train_frame["home_team_win"].astype(int))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "best_model.joblib"
    joblib.dump(
        {
            "model_name": args.model_name,
            "prediction_mode": args.prediction_mode,
            "feature_columns": feature_columns,
            "estimator": estimator,
            "training_rows": len(train_frame),
            "training_features": str(args.features),
        },
        model_path,
    )
    print(f"Wrote final model bundle to {model_path}")
    print(f"training_rows={len(train_frame)} feature_count={len(feature_columns)} model_name={args.model_name}")


def fit_final_runs_model_command(args: argparse.Namespace) -> None:
    features = read_csv_table(args.features)
    if args.prediction_mode and "prediction_mode" in features.columns:
        features = features[features["prediction_mode"] == args.prediction_mode].copy()
    for target in ["home_score", "away_score"]:
        if target not in features.columns:
            raise ValueError(f"features must include {target}")
    train_frame = features.dropna(subset=["home_score", "away_score"]).copy()
    feature_columns = [column for column in select_feature_columns(train_frame) if column not in {"home_score", "away_score"}]
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")
    x_train = train_frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    home_model = make_regressor(args.model_name, random_state=args.random_state)
    away_model = make_regressor(args.model_name, random_state=args.random_state + 1)
    home_model.fit(x_train, train_frame["home_score"].astype(float))
    away_model.fit(x_train, train_frame["away_score"].astype(float))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "runs_model.joblib"
    joblib.dump(
        {
            "model_name": args.model_name,
            "prediction_mode": args.prediction_mode,
            "feature_columns": feature_columns,
            "home_model": home_model,
            "away_model": away_model,
            "training_rows": len(train_frame),
            "training_features": str(args.features),
        },
        model_path,
    )
    print(f"Wrote final runs model bundle to {model_path}")
    print(f"training_rows={len(train_frame)} feature_count={len(feature_columns)} model_name={args.model_name}")


def fit_final_ou_model_command(args: argparse.Namespace) -> None:
    features = read_csv_table(args.features)
    if args.prediction_mode and "prediction_mode" in features.columns:
        features = features[features["prediction_mode"] == args.prediction_mode].copy()
    if "market_total_line" not in features.columns:
        if args.total_lines:
            lines = read_csv_table(args.total_lines)
            if "game_id" not in lines.columns or "total_line" not in lines.columns:
                raise ValueError("--total-lines must contain game_id,total_line")
            features = features.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
            features["market_total_line"] = pd.to_numeric(features["total_line"], errors="coerce")
        elif args.total_line is not None:
            features["market_total_line"] = args.total_line
        else:
            raise ValueError("features must include market_total_line, or provide --total-line/--total-lines.")
    elif args.total_lines:
        lines = read_csv_table(args.total_lines)
        if "game_id" not in lines.columns or "total_line" not in lines.columns:
            raise ValueError("--total-lines must contain game_id,total_line")
        features = features.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
        features["market_total_line"] = pd.to_numeric(features["market_total_line"], errors="coerce").fillna(
            pd.to_numeric(features["total_line"], errors="coerce")
        )
    elif args.total_line is not None:
        features["market_total_line"] = pd.to_numeric(features["market_total_line"], errors="coerce").fillna(args.total_line)

    required = {"home_score", "away_score", "market_total_line"}
    missing = required - set(features.columns)
    if missing:
        raise ValueError(f"features must include columns for over/under training: {sorted(missing)}")
    frame = features.copy()
    frame["actual_total"] = pd.to_numeric(frame["home_score"], errors="coerce") + pd.to_numeric(frame["away_score"], errors="coerce")
    frame["market_total_line"] = pd.to_numeric(frame["market_total_line"], errors="coerce")
    frame = frame.dropna(subset=["actual_total", "market_total_line"]).copy()
    if frame.empty:
        raise ValueError("No rows remain after requiring actual_total and market_total_line.")
    frame["market_total_over"] = (frame["actual_total"] > frame["market_total_line"]).astype(int)
    feature_columns = [
        column
        for column in select_feature_columns(frame)
        if column not in {"home_score", "away_score", "actual_total", "market_total_over", "market_closing_total_line"}
    ]
    if not feature_columns:
        raise ValueError("No numeric feature columns found.")
    x_train = frame[feature_columns].apply(pd.to_numeric, errors="coerce")
    estimator = make_classifier(args.model_name, random_state=args.random_state)
    estimator.fit(x_train, frame["market_total_over"])
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / "ou_model.joblib"
    joblib.dump(
        {
            "model_name": args.model_name,
            "prediction_mode": args.prediction_mode,
            "feature_columns": feature_columns,
            "estimator": estimator,
            "training_rows": len(frame),
            "training_features": str(args.features),
            "training_total_line": args.total_line,
            "training_total_lines": args.total_lines,
            "target": "actual_total > market_total_line",
        },
        model_path,
    )
    over_rate = frame["market_total_over"].mean()
    print(f"Wrote final over/under model bundle to {model_path}")
    print(
        f"training_rows={len(frame)} feature_count={len(feature_columns)} "
        f"model_name={args.model_name} over_rate={over_rate:.3f}"
    )


def predict_command(args: argparse.Namespace) -> None:
    bundle = joblib.load(args.model)
    features = read_csv_table(args.features)
    if args.game_ids:
        allowed = {value.strip() for value in args.game_ids.split(",") if value.strip()}
        features = features[features["game_id"].astype(str).isin(allowed)].copy()
    feature_columns = bundle["feature_columns"]
    estimator = bundle["estimator"]
    missing_columns = [column for column in feature_columns if column not in features.columns]
    if missing_columns:
        features = pd.concat(
            [features, pd.DataFrame(np.nan, index=features.index, columns=missing_columns)],
            axis=1,
        )
    x = features[feature_columns].apply(pd.to_numeric, errors="coerce")
    probabilities = estimator.predict_proba(x)[:, 1]
    for (_, row), probability in zip(features.iterrows(), probabilities, strict=False):
        result = build_prediction_result(
            float(probability),
            model_name=args.model_name or bundle.get("model_name", "unknown"),
            prediction_mode=args.prediction_mode,
            key_reasons=simple_key_reasons(row),
        )
        print(json.dumps(result.as_dict(), ensure_ascii=False))


def predict_runs_command(args: argparse.Namespace) -> None:
    bundle = joblib.load(args.model)
    features = read_csv_table(args.features)
    if args.game_ids:
        allowed = {value.strip() for value in args.game_ids.split(",") if value.strip()}
        features = features[features["game_id"].astype(str).isin(allowed)].copy()
    feature_columns = bundle["feature_columns"]
    missing_columns = [column for column in feature_columns if column not in features.columns]
    if missing_columns:
        features = pd.concat(
            [features, pd.DataFrame(np.nan, index=features.index, columns=missing_columns)],
            axis=1,
        )
    x = features[feature_columns].apply(pd.to_numeric, errors="coerce")
    pred_home = np.clip(bundle["home_model"].predict(x), 0, None)
    pred_away = np.clip(bundle["away_model"].predict(x), 0, None)

    output = features[["game_id", "game_date", "home_team", "away_team"]].copy()
    for column in ["home_score", "away_score"]:
        if column in features.columns:
            output[column] = features[column]
    output["model_name"] = bundle.get("model_name", "unknown")
    output["prediction_mode"] = args.prediction_mode
    output["pred_home_score"] = pred_home
    output["pred_away_score"] = pred_away
    output["pred_total"] = output["pred_home_score"] + output["pred_away_score"]
    output["pred_run_diff"] = output["pred_home_score"] - output["pred_away_score"]
    output["rounded_score"] = (
        output["pred_home_score"].round().astype(int).astype(str)
        + "-"
        + output["pred_away_score"].round().astype(int).astype(str)
    )

    if args.total_lines:
        lines = read_csv_table(args.total_lines)
        if "game_id" not in lines.columns or "total_line" not in lines.columns:
            raise ValueError("--total-lines must contain game_id,total_line")
        output = output.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
    elif args.total_line is not None:
        output["total_line"] = args.total_line
    else:
        output["total_line"] = np.nan

    output["ou_margin"] = output["pred_total"] - output["total_line"]
    output["ou_pick"] = np.where(
        output["total_line"].notna(),
        np.where(output["ou_margin"] > 0, "over", "under"),
        "",
    )
    output["ou_confidence"] = pd.cut(
        output["ou_margin"].abs(),
        bins=[-np.inf, args.pass_margin, args.strong_margin, np.inf],
        labels=["pass", "lean", "strong"],
    ).astype(str)

    if {"home_score", "away_score"}.issubset(output.columns):
        output["actual_total"] = output["home_score"] + output["away_score"]
        output["actual_ou"] = np.where(
            output["total_line"].notna(),
            np.where(output["actual_total"] > output["total_line"], "over", "under"),
            "",
        )
        output["ou_correct"] = np.where(
            output["total_line"].notna(),
            output["ou_pick"].eq(output["actual_ou"]),
            np.nan,
        )
        output["total_abs_error"] = (output["pred_total"] - output["actual_total"]).abs()

    if args.output:
        write_csv_table(output, args.output)
        print(f"Wrote {len(output)} run predictions to {args.output}")
    else:
        for _, row in output.iterrows():
            print(json.dumps(row.dropna().to_dict(), ensure_ascii=False))


def predict_ou_command(args: argparse.Namespace) -> None:
    bundle = joblib.load(args.model)
    features = read_csv_table(args.features)
    if args.game_ids:
        allowed = {value.strip() for value in args.game_ids.split(",") if value.strip()}
        features = features[features["game_id"].astype(str).isin(allowed)].copy()
    if "market_total_line" not in features.columns:
        if args.total_lines:
            lines = read_csv_table(args.total_lines)
            if "game_id" not in lines.columns or "total_line" not in lines.columns:
                raise ValueError("--total-lines must contain game_id,total_line")
            features = features.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
            features["market_total_line"] = pd.to_numeric(features["total_line"], errors="coerce")
        elif args.total_line is not None:
            features["market_total_line"] = args.total_line
        else:
            raise ValueError("features must include market_total_line, or provide --total-line/--total-lines.")
    elif args.total_lines:
        lines = read_csv_table(args.total_lines)
        if "game_id" not in lines.columns or "total_line" not in lines.columns:
            raise ValueError("--total-lines must contain game_id,total_line")
        features = features.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
        features["market_total_line"] = pd.to_numeric(features["market_total_line"], errors="coerce").fillna(
            pd.to_numeric(features["total_line"], errors="coerce")
        )
    elif args.total_line is not None:
        features["market_total_line"] = pd.to_numeric(features["market_total_line"], errors="coerce").fillna(args.total_line)
    feature_columns = bundle["feature_columns"]
    missing_columns = [column for column in feature_columns if column not in features.columns]
    if missing_columns:
        features = pd.concat(
            [features, pd.DataFrame(np.nan, index=features.index, columns=missing_columns)],
            axis=1,
        )
    x = features[feature_columns].apply(pd.to_numeric, errors="coerce")
    probability_over = bundle["estimator"].predict_proba(x)[:, 1]
    output = features[["game_id", "game_date", "home_team", "away_team", "market_total_line"]].copy()
    for column in ["home_score", "away_score"]:
        if column in features.columns:
            output[column] = features[column]
    output["model_name"] = bundle.get("model_name", "unknown")
    output["prediction_mode"] = args.prediction_mode
    output["prob_over"] = probability_over
    output["prob_under"] = 1.0 - output["prob_over"]
    output["ou_pick"] = np.where(output["prob_over"] >= 0.5, "over", "under")
    output["ou_edge"] = (output["prob_over"] - 0.5).abs()
    output["ou_confidence"] = pd.cut(
        output["ou_edge"],
        bins=[-np.inf, args.pass_edge, args.strong_edge, np.inf],
        labels=["pass", "lean", "strong"],
    ).astype(str)
    if {"home_score", "away_score"}.issubset(output.columns):
        output["actual_total"] = pd.to_numeric(output["home_score"], errors="coerce") + pd.to_numeric(output["away_score"], errors="coerce")
        output["actual_ou"] = np.where(output["actual_total"] > output["market_total_line"], "over", "under")
        output["ou_correct"] = output["ou_pick"].eq(output["actual_ou"])
    if args.output:
        write_csv_table(output, args.output)
        print(f"Wrote {len(output)} over/under predictions to {args.output}")
    else:
        for _, row in output.iterrows():
            print(json.dumps(row.dropna().to_dict(), ensure_ascii=False))


def predict_game_command(args: argparse.Namespace) -> None:
    """Emit win probability, expected score, and over/under signals together."""

    features = read_csv_table(args.features)
    if args.game_ids:
        allowed = {value.strip() for value in args.game_ids.split(",") if value.strip()}
        features = features[features["game_id"].astype(str).isin(allowed)].copy()

    output = features[["game_id", "game_date", "home_team", "away_team"]].copy()
    for column in ["home_score", "away_score"]:
        if column in features.columns:
            output[column] = features[column]

    win_bundle = joblib.load(args.win_model)
    win_columns = win_bundle["feature_columns"]
    win_features = features.copy()
    missing_win_columns = [column for column in win_columns if column not in win_features.columns]
    if missing_win_columns:
        win_features = pd.concat(
            [win_features, pd.DataFrame(np.nan, index=win_features.index, columns=missing_win_columns)],
            axis=1,
        )
    win_x = win_features[win_columns].apply(pd.to_numeric, errors="coerce")
    home_win_probability = win_bundle["estimator"].predict_proba(win_x)[:, 1]
    output["win_model_name"] = win_bundle.get("model_name", "unknown")
    output["home_win_probability"] = home_win_probability
    output["away_win_probability"] = 1.0 - output["home_win_probability"]
    output["win_pick"] = np.where(output["home_win_probability"] >= 0.5, output["home_team"], output["away_team"])

    runs_bundle = joblib.load(args.runs_model)
    runs_columns = runs_bundle["feature_columns"]
    runs_features = features.copy()
    missing_runs_columns = [column for column in runs_columns if column not in runs_features.columns]
    if missing_runs_columns:
        runs_features = pd.concat(
            [runs_features, pd.DataFrame(np.nan, index=runs_features.index, columns=missing_runs_columns)],
            axis=1,
        )
    runs_x = runs_features[runs_columns].apply(pd.to_numeric, errors="coerce")
    pred_home = np.clip(runs_bundle["home_model"].predict(runs_x), 0, None)
    pred_away = np.clip(runs_bundle["away_model"].predict(runs_x), 0, None)
    output["runs_model_name"] = runs_bundle.get("model_name", "unknown")
    output["pred_home_score"] = pred_home
    output["pred_away_score"] = pred_away
    output["pred_total"] = output["pred_home_score"] + output["pred_away_score"]
    output["pred_run_diff"] = output["pred_home_score"] - output["pred_away_score"]
    output["rounded_score"] = (
        output["pred_home_score"].round().astype(int).astype(str)
        + "-"
        + output["pred_away_score"].round().astype(int).astype(str)
    )

    if "market_total_line" in features.columns:
        output["total_line"] = pd.to_numeric(features["market_total_line"], errors="coerce")
        if args.total_lines:
            lines = read_csv_table(args.total_lines)
            if "game_id" not in lines.columns or "total_line" not in lines.columns:
                raise ValueError("--total-lines must contain game_id,total_line")
            output = output.merge(lines[["game_id", "total_line"]].rename(columns={"total_line": "fallback_total_line"}), on="game_id", how="left")
            output["total_line"] = output["total_line"].fillna(pd.to_numeric(output["fallback_total_line"], errors="coerce"))
            output = output.drop(columns=["fallback_total_line"])
        elif args.total_line is not None:
            output["total_line"] = output["total_line"].fillna(args.total_line)
    elif args.total_lines:
        lines = read_csv_table(args.total_lines)
        if "game_id" not in lines.columns or "total_line" not in lines.columns:
            raise ValueError("--total-lines must contain game_id,total_line")
        output = output.merge(lines[["game_id", "total_line"]], on="game_id", how="left")
    elif args.total_line is not None:
        output["total_line"] = args.total_line
    else:
        output["total_line"] = np.nan

    output["runs_ou_margin"] = output["pred_total"] - output["total_line"]
    output["runs_ou_pick"] = np.where(
        output["total_line"].notna(),
        np.where(output["runs_ou_margin"] > 0, "over", "under"),
        "",
    )
    output["runs_ou_confidence"] = pd.cut(
        output["runs_ou_margin"].abs(),
        bins=[-np.inf, args.pass_margin, args.strong_margin, np.inf],
        labels=["pass", "lean", "strong"],
    ).astype(str)

    if args.ou_model:
        ou_bundle = joblib.load(args.ou_model)
        ou_features = features.copy()
        if "market_total_line" not in ou_features.columns:
            ou_features["market_total_line"] = output["total_line"]
        ou_columns = ou_bundle["feature_columns"]
        missing_ou_columns = [column for column in ou_columns if column not in ou_features.columns]
        if missing_ou_columns:
            ou_features = pd.concat(
                [ou_features, pd.DataFrame(np.nan, index=ou_features.index, columns=missing_ou_columns)],
                axis=1,
            )
        ou_x = ou_features[ou_columns].apply(pd.to_numeric, errors="coerce")
        probability_over = ou_bundle["estimator"].predict_proba(ou_x)[:, 1]
        output["ou_model_name"] = ou_bundle.get("model_name", "unknown")
        output["direct_prob_over"] = probability_over
        output["direct_prob_under"] = 1.0 - output["direct_prob_over"]
        output["direct_ou_pick"] = np.where(output["direct_prob_over"] >= 0.5, "over", "under")
        output["direct_ou_edge"] = (output["direct_prob_over"] - 0.5).abs()
        output["direct_ou_confidence"] = pd.cut(
            output["direct_ou_edge"],
            bins=[-np.inf, args.pass_edge, args.strong_edge, np.inf],
            labels=["pass", "lean", "strong"],
        ).astype(str)

    if {"home_score", "away_score"}.issubset(output.columns):
        home_scores = pd.to_numeric(output["home_score"], errors="coerce")
        away_scores = pd.to_numeric(output["away_score"], errors="coerce")
        output["actual_total"] = home_scores + away_scores
        has_winner = home_scores.notna() & away_scores.notna() & home_scores.ne(away_scores)
        output["actual_winner"] = np.where(
            has_winner,
            np.where(home_scores > away_scores, output["home_team"], output["away_team"]),
            np.nan,
        )
        output["win_correct"] = output["win_pick"].eq(output["actual_winner"])
        output["actual_ou"] = np.where(
            output["total_line"].notna(),
            np.where(output["actual_total"] > output["total_line"], "over", "under"),
            "",
        )
        output["runs_ou_correct"] = np.where(
            output["total_line"].notna(),
            output["runs_ou_pick"].eq(output["actual_ou"]),
            np.nan,
        )
        if "direct_ou_pick" in output.columns:
            output["direct_ou_correct"] = np.where(
                output["total_line"].notna(),
                output["direct_ou_pick"].eq(output["actual_ou"]),
                np.nan,
            )
        output["total_abs_error"] = (output["pred_total"] - output["actual_total"]).abs()

    output["prediction_mode"] = args.prediction_mode
    if args.output:
        write_csv_table(output, args.output)
        print(f"Wrote {len(output)} combined game predictions to {args.output}")
    else:
        for _, row in output.iterrows():
            print(json.dumps(row.dropna().to_dict(), ensure_ascii=False))


def win_pick_rule_report_command(args: argparse.Namespace) -> None:
    predictions = read_csv_table(args.predictions)
    if args.exclude_dates:
        excluded = {value.strip() for value in args.exclude_dates.split(",") if value.strip()}
        if args.date_column not in predictions.columns:
            raise ValueError(f"--date-column {args.date_column!r} is missing from predictions")
        dates = pd.to_datetime(predictions[args.date_column], errors="coerce").dt.strftime("%Y-%m-%d")
        predictions = predictions[~dates.isin(excluded)].copy()

    ruled = apply_win_pick_rules(
        predictions,
        probability_column=args.probability_column,
        home_team_column=args.home_team_column,
        away_team_column=args.away_team_column,
        actual_winner_column=args.actual_winner_column,
        lean_threshold=args.lean_threshold,
        strong_threshold=args.strong_threshold,
    )
    scored = _scored_prediction_rows(ruled, actual_winner_column=args.actual_winner_column)
    summary_frame = scored if args.scored_only else ruled
    summary = summarize_win_pick_rules(summary_frame)

    daily = pd.DataFrame()
    if args.date_column in scored.columns:
        daily_rows = []
        date_values = pd.to_datetime(scored[args.date_column], errors="coerce").dt.strftime("%Y-%m-%d")
        for date, group in scored.assign(_rule_date=date_values).groupby("_rule_date", dropna=False, sort=True):
            day_summary = summarize_win_pick_rules(group)
            by_rule = day_summary.set_index("rule")
            actionable = by_rule.loc["actionable"]
            daily_rows.append(
                {
                    "date": date,
                    "scored_games": int(len(group)),
                    "pass_games": int(by_rule.loc["pass", "games"]) if "pass" in by_rule.index else 0,
                    "lean_games": int(by_rule.loc["lean", "games"]) if "lean" in by_rule.index else 0,
                    "strong_games": int(by_rule.loc["strong", "games"]) if "strong" in by_rule.index else 0,
                    "picks": int(actionable["picks"]),
                    "hits": float(actionable["hits"]),
                    "accuracy": float(actionable["accuracy"]) if pd.notna(actionable["accuracy"]) else np.nan,
                    "coverage": float(actionable["coverage"]) if pd.notna(actionable["coverage"]) else np.nan,
                    "avg_confidence": float(actionable["avg_confidence"]) if pd.notna(actionable["avg_confidence"]) else np.nan,
                }
            )
        daily = pd.DataFrame(daily_rows)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "predictions": output_dir / "win_pick_rules.csv",
        "summary": output_dir / "win_pick_rule_summary.csv",
        "daily": output_dir / "win_pick_rule_daily.csv",
    }
    write_csv_table(ruled, paths["predictions"])
    write_csv_table(summary, paths["summary"])
    if not daily.empty:
        write_csv_table(daily, paths["daily"])

    print(f"Wrote predictions: {paths['predictions']}")
    print(f"Wrote summary: {paths['summary']}")
    if not daily.empty:
        print(f"Wrote daily: {paths['daily']}")


def oof_selective_pick_report_command(args: argparse.Namespace) -> None:
    features = read_feature_tables(args.features)
    model_values = [value.strip() for value in args.models.split(",") if value.strip()]
    challenger_values = [value.strip() for value in args.challenger_models.split(",") if value.strip()]
    holdout_values = [int(value.strip()) for value in args.holdout_seasons.split(",") if value.strip()]
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    oof = run_oof_win_predictions(
        features,
        model_names=model_values,
        holdout_seasons=holdout_values,
        prediction_mode=args.prediction_mode,
        random_state=args.random_state,
    )
    individual_frames = []
    for model_name, group in oof.groupby("model_name", sort=True):
        ruled = apply_win_pick_rules(
            group,
            lean_threshold=args.lean_threshold,
            strong_threshold=args.strong_threshold,
        )
        summary = summarize_win_pick_rules(ruled)
        summary.insert(0, "rule_name", f"model:{model_name}")
        summary.insert(1, "model_name", model_name)
        individual_frames.append(summary)

    individual_summary = pd.concat(individual_frames, ignore_index=True) if individual_frames else pd.DataFrame()
    agreement = apply_model_agreement_pick_rules(
        oof,
        primary_model=args.primary_model,
        challenger_models=challenger_values,
        lean_threshold=args.lean_threshold,
        strong_threshold=args.strong_threshold,
    )
    agreement_summary = summarize_win_pick_rules(agreement)
    agreement_summary.insert(0, "rule_name", "agreement")
    agreement_summary.insert(1, "model_name", args.primary_model)
    all_summary = pd.concat([individual_summary, agreement_summary], ignore_index=True)

    season_frames = []
    for season, group in agreement.groupby("holdout_season", sort=True):
        season_summary = summarize_win_pick_rules(group)
        season_summary.insert(0, "holdout_season", season)
        season_frames.append(season_summary)
    season_summary = pd.concat(season_frames, ignore_index=True) if season_frames else pd.DataFrame()

    paths = {
        "oof_predictions": output_dir / "oof_win_predictions.csv",
        "agreement_predictions": output_dir / "agreement_pick_rules.csv",
        "summary": output_dir / "selective_pick_summary.csv",
        "season_summary": output_dir / "selective_pick_by_holdout.csv",
        "markdown": output_dir / "summary.md",
    }
    write_csv_table(oof, paths["oof_predictions"])
    write_csv_table(agreement, paths["agreement_predictions"])
    write_csv_table(all_summary, paths["summary"])
    write_csv_table(season_summary, paths["season_summary"])

    actionable = all_summary[all_summary["rule"].eq("actionable")].copy()
    agreement_actionable = season_summary[season_summary["rule"].eq("actionable")] if not season_summary.empty else season_summary
    lines = [
        "# OOF Selective Pick Report",
        "",
        f"Models: `{', '.join(model_values)}`",
        f"Primary model: `{args.primary_model}`",
        f"Agreement challengers: `{', '.join(challenger_values)}`",
        f"Thresholds: lean `{args.lean_threshold}`, strong `{args.strong_threshold}`",
        "",
        "## Actionable Summary",
        "",
        _markdown_table(actionable),
        "",
        "## Agreement By Holdout",
        "",
        _markdown_table(agreement_actionable),
        "",
    ]
    paths["markdown"].write_text("\n".join(lines), encoding="utf-8")
    for name, path in paths.items():
        print(f"Wrote {name}: {path}")


def predict_games_by_kst_date_command(args: argparse.Namespace) -> None:
    mlb_date = args.mlb_date or kst_date_to_mlb_date(args.date_kst)
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    standardized_dir = output_dir / "standardized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    standardized_dir.mkdir(parents=True, exist_ok=True)

    schedule_path = raw_dir / f"schedule_{mlb_date}.csv"
    boxscore_dir = raw_dir / f"boxscores_{mlb_date}"
    manifest_path = raw_dir / f"manifest_{mlb_date}.csv"
    features_path = output_dir / "features_pre_lineup.csv"
    predictions_path = output_dir / "predictions.csv"
    readable_path = output_dir / "predictions_readable.csv"

    collector = MLBStatsApiCollector()
    schedule = collector.schedule(mlb_date, mlb_date)
    if args.game_types:
        allowed = {value.strip() for value in args.game_types.split(",") if value.strip()}
        schedule = schedule[schedule["game_type"].astype(str).isin(allowed)].copy()
    schedule = schedule.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last")
    write_csv_table(schedule, schedule_path)
    print(f"Wrote schedule: {schedule_path} ({len(schedule)} rows)")

    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    workers = args.workers or default_collection_workers()
    paths = collector.save_boxscores(
        game_ids,
        boxscore_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Prediction snapshots"),
    )
    manifest = pd.DataFrame(
        {
            "game_id": game_ids,
            "snapshot_path": [str(path) for path in paths],
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "lineup_source": "mlb_stats_api_boxscore_snapshot",
        }
    )
    write_csv_table(manifest, manifest_path)
    print(f"Wrote snapshots: {boxscore_dir} ({len(paths)} files)")

    standardize_mlb_stats_api_boxscores(
        schedule_csv=schedule_path,
        boxscore_dir=boxscore_dir,
        output_dir=standardized_dir,
        prediction_mode="pre_lineup",
        lineup_source="mlb_stats_api_boxscore_snapshot",
        captured_at=manifest["captured_at"].iloc[0] if not manifest.empty else None,
        lineup_confidence=1.0,
    )

    batting_logs = args.batting_logs
    pitcher_logs = args.pitcher_logs
    if args.season_to_date_standardized:
        season_dir = Path(args.season_to_date_standardized)
        batting_logs = str(season_dir / "batting_logs.csv")
        pitcher_logs = str(season_dir / "pitcher_logs.csv")

    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="pre_lineup"))
    features = builder.build(
        games=read_csv_table(standardized_dir / "games.csv"),
        batting_logs=read_csv_table(batting_logs),
        pitcher_logs=read_csv_table(pitcher_logs),
        lineups=read_csv_table(standardized_dir / "lineups.csv"),
        weather=read_csv_table(standardized_dir / "weather.csv"),
        park_factors=read_csv_table(args.park_factors) if args.park_factors else None,
        venues=read_csv_table(args.venues) if args.venues else None,
    )
    write_csv_table(features, features_path)
    print(f"Wrote features: {features_path} ({len(features)} rows)")

    predict_args = argparse.Namespace(
        features=str(features_path),
        win_model=args.win_model,
        runs_model=args.runs_model,
        ou_model=args.ou_model,
        prediction_mode="pre_lineup",
        game_ids=None,
        total_line=args.total_line,
        total_lines=args.total_lines,
        pass_margin=args.pass_margin,
        strong_margin=args.strong_margin,
        pass_edge=args.pass_edge,
        strong_edge=args.strong_edge,
        output=str(predictions_path),
    )
    predict_game_command(predict_args)
    predictions = read_csv_table(predictions_path)
    readable = _readable_prediction_table(
        predictions,
        schedule=schedule,
        korean=not args.ascii_team_names,
        lean_threshold=args.lean_threshold,
        strong_threshold=args.strong_threshold,
    )
    write_csv_table(readable, readable_path)
    print(f"Wrote readable predictions: {readable_path}")


def review_game_predictions_command(args: argparse.Namespace) -> None:
    predictions = read_csv_table(args.predictions)
    if args.schedule:
        schedule = read_csv_table(args.schedule)
    else:
        if not args.mlb_date:
            raise ValueError("--mlb-date is required when --schedule is not provided.")
        schedule = MLBStatsApiCollector().schedule(args.mlb_date, args.mlb_date)

    score_columns = ["game_id", "status", "home_score", "away_score"]
    score_columns = [column for column in score_columns if column in schedule.columns]
    reviewed = predictions.merge(schedule[score_columns], on="game_id", how="left", suffixes=("", "_review"))
    home_scores = pd.to_numeric(reviewed.get("home_score_review", reviewed.get("home_score")), errors="coerce")
    away_scores = pd.to_numeric(reviewed.get("away_score_review", reviewed.get("away_score")), errors="coerce")
    reviewed["review_home_score"] = home_scores
    reviewed["review_away_score"] = away_scores
    reviewed["review_scored"] = home_scores.notna() & away_scores.notna() & home_scores.ne(away_scores)
    reviewed["review_actual_winner"] = np.where(
        reviewed["review_scored"],
        np.where(home_scores > away_scores, reviewed["home_team"], reviewed["away_team"]),
        "",
    )
    reviewed["review_win_correct"] = np.where(
        reviewed["review_scored"],
        reviewed["win_pick"].astype(str).eq(reviewed["review_actual_winner"].astype(str)),
        np.nan,
    )
    if {"pred_home_score", "pred_away_score"}.issubset(reviewed.columns):
        reviewed["review_actual_total"] = home_scores + away_scores
        reviewed["review_total_abs_error"] = (
            pd.to_numeric(reviewed["pred_home_score"], errors="coerce")
            + pd.to_numeric(reviewed["pred_away_score"], errors="coerce")
            - reviewed["review_actual_total"]
        ).abs()

    scored = reviewed[reviewed["review_scored"]].copy()
    summary = pd.DataFrame(
        [
            {
                "games": int(len(reviewed)),
                "scored_games": int(len(scored)),
                "win_hits": float(scored["review_win_correct"].astype(bool).sum()) if not scored.empty else 0.0,
                "win_accuracy": float(scored["review_win_correct"].astype(bool).mean()) if not scored.empty else np.nan,
                "total_mae": float(scored["review_total_abs_error"].mean()) if "review_total_abs_error" in scored.columns and not scored.empty else np.nan,
            }
        ]
    )
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    review_path = output_dir / "prediction_review.csv"
    summary_path = output_dir / "prediction_review_summary.csv"
    write_csv_table(reviewed, review_path)
    write_csv_table(summary, summary_path)
    print(f"Wrote review: {review_path}")
    print(f"Wrote summary: {summary_path}")


def prepare_season_to_date_dataset_command(args: argparse.Namespace) -> None:
    collector = MLBStatsApiCollector()
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    boxscore_dir = raw_dir / "boxscores"
    standardized_dir = output_dir / "standardized"
    raw_dir.mkdir(parents=True, exist_ok=True)
    standardized_dir.mkdir(parents=True, exist_ok=True)

    start_date = args.start_date or f"{args.season}-01-01"
    schedule = collector.schedule(start_date, args.end_date)
    if args.game_types:
        allowed = {value.strip() for value in args.game_types.split(",") if value.strip()}
        schedule = schedule[schedule["game_type"].astype(str).isin(allowed)].copy()
    home_scores = pd.to_numeric(schedule["home_score"], errors="coerce") if "home_score" in schedule.columns else pd.Series(np.nan, index=schedule.index)
    away_scores = pd.to_numeric(schedule["away_score"], errors="coerce") if "away_score" in schedule.columns else pd.Series(np.nan, index=schedule.index)
    status = schedule["status"].astype(str).str.lower() if "status" in schedule.columns else pd.Series("", index=schedule.index)
    completed = home_scores.notna() & away_scores.notna() & ~status.isin({"scheduled", "pre-game", "in progress"})
    schedule = schedule[completed].sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last").copy()
    if args.limit:
        schedule = schedule.head(args.limit).copy()

    schedule_path = raw_dir / "schedule.csv"
    people_path = raw_dir / "people.csv"
    write_csv_table(schedule, schedule_path)
    print(f"Wrote completed season-to-date schedule: {schedule_path} ({len(schedule)} rows)")

    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    workers = args.workers or default_collection_workers()
    collector.save_boxscores(
        game_ids,
        boxscore_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Season-to-date boxscores"),
    )

    initial_outputs = standardize_mlb_stats_api_boxscores(
        schedule_csv=schedule_path,
        boxscore_dir=boxscore_dir,
        output_dir=standardized_dir,
        prediction_mode="confirmed_lineup",
    )
    player_ids: set[int] = set()
    for path in initial_outputs.values():
        frame = read_csv_table(path)
        for column in ["player_id", "home_sp_id", "away_sp_id"]:
            if column in frame.columns:
                values = pd.to_numeric(frame[column], errors="coerce").dropna().astype(int)
                player_ids.update(values.tolist())
    if player_ids:
        people = collector.people(sorted(player_ids))
        write_csv_table(people, people_path)
        standardize_mlb_stats_api_boxscores(
            schedule_csv=schedule_path,
            boxscore_dir=boxscore_dir,
            output_dir=standardized_dir,
            prediction_mode="confirmed_lineup",
            people_csv=people_path,
        )
        print(f"Wrote people metadata: {people_path} ({len(people)} rows)")
    print(f"Wrote standardized season-to-date tables: {standardized_dir}")


def collect_statcast_command(args: argparse.Namespace) -> None:
    collector = PyBaseballCollector()
    frame = collector.statcast(args.start_date, args.end_date)
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} Statcast rows to {args.output}")


def aggregate_statcast_command(args: argparse.Namespace) -> None:
    events = read_csv_table(args.statcast)
    batting = aggregate_statcast_batting(events)
    pitching = aggregate_statcast_pitching(events)
    write_csv_table(batting, args.batting_output)
    write_csv_table(pitching, args.pitching_output)
    print(f"Wrote {len(batting)} Statcast batting quality rows to {args.batting_output}")
    print(f"Wrote {len(pitching)} Statcast pitching quality rows to {args.pitching_output}")


def merge_statcast_logs_command(args: argparse.Namespace) -> None:
    batting, pitching = merge_statcast_quality(
        batting_logs=read_csv_table(args.batting_logs),
        pitcher_logs=read_csv_table(args.pitcher_logs),
        statcast_batting=read_csv_table(args.statcast_batting),
        statcast_pitching=read_csv_table(args.statcast_pitching),
    )
    write_csv_table(batting, args.batting_output)
    write_csv_table(pitching, args.pitching_output)
    print(f"Wrote {len(batting)} enriched batting log rows to {args.batting_output}")
    print(f"Wrote {len(pitching)} enriched pitcher log rows to {args.pitching_output}")


def collect_fangraphs_command(args: argparse.Namespace) -> None:
    collector = PyBaseballCollector()
    if args.table == "batting":
        frame = collector.batting_stats(args.season)
    else:
        frame = collector.pitching_stats(args.season)
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} FanGraphs {args.table} rows to {args.output}")


def collect_balldontlie_lineups_command(args: argparse.Namespace) -> None:
    collector = BallDontLieMLBCollector(api_key=args.api_key)
    game_ids = [value.strip() for value in args.game_ids.split(",") if value.strip()] if args.game_ids else None
    dates = [value.strip() for value in args.dates.split(",") if value.strip()] if args.dates else None
    if not game_ids and not dates:
        raise ValueError("Provide --dates or --game-ids to keep lineup collection scoped.")
    path = collector.save_lineups(args.output, game_ids=game_ids, dates=dates, per_page=args.per_page)
    print(f"Wrote BALLDONTLIE MLB lineup JSON to {path}")


def collect_mykbo_season_pages_command(args: argparse.Namespace) -> None:
    collector = MyKBOStatsCollector()
    pages = [value.strip() for value in args.pages.split(",") if value.strip()] if args.pages else None
    output_root = Path(args.output_root)
    total_pages = 0
    total_tables = 0
    for season in range(args.start_season, args.end_season + 1):
        raw_dir = output_root / "raw" / "mykbo_stats" / str(season)
        parsed_dir = output_root / "standardized" / "kbo" / str(season) / "mykbo_tables"
        paths = collector.save_season_pages(
            season,
            raw_dir,
            pages=pages,
            skip_existing=not args.no_skip_existing,
        )
        total_pages += len(paths)
        if args.parse_tables:
            for path in paths:
                table_paths = collector.write_html_tables(path, parsed_dir)
                total_tables += len(table_paths)
        print(
            f"Collected MyKBO season {season}: pages={len(paths)} "
            f"raw_dir={raw_dir} parsed_dir={parsed_dir if args.parse_tables else 'skipped'}",
            flush=True,
        )
    print(f"Collected MyKBO pages={total_pages} parsed_outputs={total_tables}")


def collect_mykbo_schedule_weeks_command(args: argparse.Namespace) -> None:
    collector = MyKBOStatsCollector()
    raw_dir = Path(args.output_root) / "raw" / "mykbo_stats" / "schedule_weeks"
    parsed_dir = Path(args.output_root) / "standardized" / "kbo" / "schedule_weeks" / "mykbo_tables"
    paths = collector.save_schedule_weeks(
        args.start_date,
        args.end_date,
        raw_dir,
        skip_existing=not args.no_skip_existing,
    )
    parsed_count = 0
    if args.parse_tables:
        for path in paths:
            parsed_count += len(collector.write_html_tables(path, parsed_dir))
    print(
        f"Collected MyKBO schedule week pages={len(paths)} "
        f"raw_dir={raw_dir} parsed_outputs={parsed_count} parsed_dir={parsed_dir if args.parse_tables else 'skipped'}"
    )


def collect_mykbo_game_pages_command(args: argparse.Namespace) -> None:
    games = read_csv_table(args.games)
    if args.final_only and "is_final" in games.columns:
        games = games[pd.to_numeric(games["is_final"], errors="coerce").fillna(0).eq(1)].copy()
    paths = MyKBOStatsCollector().save_game_pages(
        games,
        args.output_dir,
        limit=args.limit,
        skip_existing=not args.no_skip_existing,
        delay=args.delay,
        max_workers=args.workers,
    )
    parsed_count = 0
    if args.parse_tables:
        parsed_dir = Path(args.parsed_dir) if args.parsed_dir else Path(args.output_dir).with_name(Path(args.output_dir).name + "_tables")
        for path in paths:
            parsed_count += len(MyKBOStatsCollector.write_html_tables(path, parsed_dir))
        print(f"Parsed MyKBO game pages to {parsed_dir}: outputs={parsed_count}")
    print(f"Collected MyKBO game pages={len(paths)} output_dir={args.output_dir}")


def standardize_mykbo_tables_command(args: argparse.Namespace) -> None:
    outputs = standardize_mykbo_tables(args.input_dir, args.output_dir, season=args.season)
    for name, path in outputs.items():
        frame = read_csv_table(path)
        print(f"Wrote {name}: {path} ({len(frame)} rows)")


def standardize_mykbo_schedule_command(args: argparse.Namespace) -> None:
    path = standardize_mykbo_schedule_links(args.input_dir, args.output)
    frame = read_csv_table(path)
    finals = int(pd.to_numeric(frame.get("is_final", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    canceled = int(pd.to_numeric(frame.get("is_canceled", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    print(f"Wrote MyKBO schedule games: {path} ({len(frame)} rows, finals={finals}, canceled={canceled})")


def standardize_mykbo_game_tables_command(args: argparse.Namespace) -> None:
    outputs = standardize_mykbo_game_tables(args.input_dir, args.games, args.output_dir)
    for name, path in outputs.items():
        frame = read_csv_table(path)
        print(f"Wrote {name}: {path} ({len(frame)} rows)")


def standardize_balldontlie_lineups_command(args: argparse.Namespace) -> None:
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    game_map = read_csv_table(args.game_id_map) if args.game_id_map else None
    player_map = read_csv_table(args.player_id_map) if args.player_id_map else None
    lineups = BallDontLieMLBCollector.normalize_lineups(
        payload,
        captured_at=args.captured_at,
        prediction_mode=args.prediction_mode,
        game_id_map=game_map,
        player_id_map=player_map,
    )
    write_csv_table(lineups, args.output)
    print(f"Wrote {len(lineups)} projected lineup rows to {args.output}")


def write_manual_lineup_template_command(args: argparse.Namespace) -> None:
    game_ids = [value.strip() for value in args.game_ids.split(",") if value.strip()] if args.game_ids else None
    template = manual_lineup_template(read_csv_table(args.games), game_ids=game_ids)
    write_csv_table(template, args.output)
    print(f"Wrote {len(template)} manual lineup template rows to {args.output}")


def write_market_lines_template_command(args: argparse.Namespace) -> None:
    game_ids = [value.strip() for value in args.game_ids.split(",") if value.strip()] if args.game_ids else None
    template = market_lines_template(read_csv_table(args.games), game_ids=game_ids)
    write_csv_table(template, args.output)
    print(f"Wrote {len(template)} market line template rows to {args.output}")


def standardize_manual_lineups_command(args: argparse.Namespace) -> None:
    id_map = read_csv_table(args.id_map) if args.id_map else None
    lineups = standardize_manual_lineups(
        read_csv_table(args.input),
        id_map=id_map,
        season=args.season,
        prediction_mode=args.prediction_mode,
        lineup_source=args.lineup_source,
        captured_at=args.captured_at,
    )
    write_csv_table(lineups, args.output)
    mapped = pd.to_numeric(lineups["player_id"], errors="coerce").notna().sum() if not lineups.empty else 0
    print(f"Wrote {len(lineups)} manual lineup rows to {args.output} (player_id_non_null={mapped})")


def collect_mlb_schedule_command(args: argparse.Namespace) -> None:
    collector = MLBStatsApiCollector()
    frame = collector.schedule(
        args.start_date,
        args.end_date,
        sport_id=args.sport_id,
        hydrate=args.hydrate,
    )
    write_csv_table(frame, args.output)
    print(f"Wrote {len(frame)} MLB Stats API schedule rows to {args.output}")


def _collection_progress(label: str):
    last_reported = 0

    def progress(downloaded: int, skipped: int, failed: int, total: int) -> None:
        nonlocal last_reported
        completed = downloaded + skipped + failed
        should_report = completed == total or completed - last_reported >= 50
        if should_report:
            last_reported = completed
            print(
                f"{label}: {completed}/{total} "
                f"(downloaded={downloaded}, skipped={skipped}, failed={failed})",
                flush=True,
            )

    return progress


def collect_mlb_boxscores_command(args: argparse.Namespace) -> None:
    schedule = read_csv_table(args.games)
    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    if args.limit:
        game_ids = game_ids[: args.limit]
    workers = args.workers or default_collection_workers()
    print(f"Collecting {len(game_ids)} MLB Stats API boxscores with {workers} workers", flush=True)
    paths = MLBStatsApiCollector().save_boxscores(
        game_ids,
        args.output_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Boxscores"),
    )
    print(f"Wrote {len(paths)} MLB Stats API boxscore JSON files to {args.output_dir}")


def collect_mlb_lineup_snapshots_command(args: argparse.Namespace) -> None:
    schedule = read_csv_table(args.games)
    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    if args.limit:
        game_ids = game_ids[: args.limit]
    captured_at = args.captured_at or datetime.now(timezone.utc).isoformat()
    workers = args.workers or default_collection_workers()
    print(f"Collecting {len(game_ids)} MLB Stats API lineup snapshots with {workers} workers", flush=True)
    paths = MLBStatsApiCollector().save_boxscores(
        game_ids,
        args.output_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Lineup snapshots"),
    )
    manifest = pd.DataFrame(
        {
            "game_id": game_ids,
            "snapshot_path": [str(path) for path in paths],
            "captured_at": captured_at,
            "lineup_source": "mlb_stats_api_boxscore_snapshot",
        }
    )
    if args.manifest:
        write_csv_table(manifest, args.manifest)
        print(f"Wrote lineup snapshot manifest to {args.manifest}")
    print(f"Wrote {len(paths)} MLB Stats API lineup snapshot JSON files to {args.output_dir}")


def collect_mlb_feeds_command(args: argparse.Namespace) -> None:
    schedule = read_csv_table(args.games)
    game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
    if args.limit:
        game_ids = game_ids[: args.limit]
    workers = args.workers or default_collection_workers()
    print(f"Collecting {len(game_ids)} MLB Stats API feeds with {workers} workers", flush=True)
    paths = MLBStatsApiCollector().save_game_feeds(
        game_ids,
        args.output_dir,
        skip_existing=not args.no_skip_existing,
        workers=workers,
        progress_callback=_collection_progress("Feeds"),
    )
    print(f"Wrote {len(paths)} MLB Stats API live feed JSON files to {args.output_dir}")


def collect_mlb_people_command(args: argparse.Namespace) -> None:
    player_ids: set[int] = set()
    for path in args.inputs:
        frame = read_csv_table(path)
        for column in args.id_columns.split(","):
            if column in frame.columns:
                values = pd.to_numeric(frame[column], errors="coerce").dropna().astype(int)
                player_ids.update(values.tolist())
    people = MLBStatsApiCollector().people(sorted(player_ids))
    write_csv_table(people, args.output)
    print(f"Wrote {len(people)} MLB Stats API people rows to {args.output}")


def collect_mlb_venues_command(args: argparse.Namespace) -> None:
    venue_ids: set[int] = set()
    for path in args.inputs:
        frame = read_csv_table(path)
        if "venue_id" not in frame.columns:
            continue
        values = pd.to_numeric(frame["venue_id"], errors="coerce").dropna().astype(int)
        venue_ids.update(values.tolist())
    venues = MLBStatsApiCollector().venues(sorted(venue_ids))
    write_csv_table(venues, args.output)
    print(f"Wrote {len(venues)} MLB Stats API venue rows to {args.output}")


def augment_weather_openmeteo_command(args: argparse.Namespace) -> None:
    augmented = augment_weather_with_open_meteo(
        games=read_csv_table(args.games),
        weather=read_csv_table(args.weather),
        venues=read_csv_table(args.venues),
        collector=OpenMeteoArchiveCollector(),
    )
    write_csv_table(augmented, args.output)
    filled = pd.to_numeric(augmented.get("humidity"), errors="coerce").notna().sum()
    print(f"Wrote {len(augmented)} weather rows to {args.output} (humidity_non_null={filled})")


def collect_retrosheet_command(args: argparse.Namespace) -> None:
    path = RetrosheetCollector().download(args.dataset, args.output)
    print(f"Wrote Retrosheet {args.dataset} to {path}")


def collect_lahman_command(args: argparse.Namespace) -> None:
    collector = LahmanCollector()
    if args.archive:
        path = collector.download_archive(args.output)
    else:
        path = collector.download_table(args.table, args.output)
    print(f"Wrote Lahman data to {path}")


def collect_chadwick_people_command(args: argparse.Namespace) -> None:
    path = ChadwickRegisterCollector().download_people(args.output)
    print(f"Wrote Chadwick register people.csv to {path}")


def build_id_map_command(args: argparse.Namespace) -> None:
    path = write_id_map(
        chadwick_people_csv=args.chadwick_people,
        mlb_people_csvs=args.mlb_people or [],
        output=args.output,
    )
    id_map = read_csv_table(path)
    print(f"Wrote {len(id_map)} ID map rows to {path}")


def build_external_lineup_id_maps_command(args: argparse.Namespace) -> None:
    provider_lineups = read_csv_table(args.provider_lineups)
    if not args.game_map_output and not args.player_map_output:
        raise ValueError("Provide --game-map-output and/or --player-map-output.")
    if args.game_map_output:
        if not args.mlb_games:
            raise ValueError("--mlb-games is required with --game-map-output.")
        game_map = build_external_game_id_map(provider_lineups, read_csv_table(args.mlb_games))
        write_csv_table(game_map, args.game_map_output)
        print(f"Wrote {len(game_map)} external game ID map rows to {args.game_map_output}")
    if args.player_map_output:
        if not args.id_map:
            raise ValueError("--id-map is required with --player-map-output.")
        player_map = build_external_player_id_map(
            provider_lineups,
            read_csv_table(args.id_map),
            season=args.season,
        )
        write_csv_table(player_map, args.player_map_output)
        print(f"Wrote {len(player_map)} external player ID map rows to {args.player_map_output}")


def download_url_command(args: argparse.Namespace) -> None:
    path = download_url(args.url, args.output)
    print(f"Wrote {args.url} to {path}")


def standardize_mlb_boxscores_command(args: argparse.Namespace) -> None:
    outputs = standardize_mlb_stats_api_boxscores(
        schedule_csv=args.schedule,
        boxscore_dir=args.boxscore_dir,
        output_dir=args.output_dir,
        prediction_mode=args.prediction_mode,
        people_csv=args.people,
        lineup_source=args.lineup_source,
        captured_at=args.captured_at,
        lineup_confidence=args.lineup_confidence,
    )
    for name, path in outputs.items():
        print(f"Wrote {name}: {path}")


def standardize_retrosheet_command(args: argparse.Namespace) -> None:
    seasons = [int(value.strip()) for value in args.seasons.split(",") if value.strip()] if args.seasons else None
    outputs = standardize_retrosheet_tables(
        gameinfo_csv=args.gameinfo,
        teamstats_csv=args.teamstats,
        batting_csv=args.batting,
        pitching_csv=args.pitching,
        output_dir=args.output_dir,
        seasons=seasons,
    )
    for name, path in outputs.items():
        print(f"Wrote {name}: {path}")


def collect_mlb_season_dataset_command(args: argparse.Namespace) -> None:
    collector = MLBStatsApiCollector()
    root = Path(args.output_root)
    raw_root = root / "raw" / "mlb_stats_api"
    standardized_root = root / "standardized"
    processed_root = root / "processed"
    raw_root.mkdir(parents=True, exist_ok=True)
    standardized_root.mkdir(parents=True, exist_ok=True)
    processed_root.mkdir(parents=True, exist_ok=True)

    for season in range(args.start_season, args.end_season + 1):
        season_label = str(season)
        print(f"=== Season {season_label} ===", flush=True)
        schedule_path = raw_root / f"schedule_{season_label}.csv"
        boxscore_dir = raw_root / f"boxscores_{season_label}"
        people_path = raw_root / f"people_{season_label}.csv"
        standardized_dir = standardized_root / f"mlb_stats_api_{season_label}"
        feature_path = processed_root / f"features_confirmed_{season_label}.csv"

        if schedule_path.exists() and not args.refresh_schedule:
            schedule = read_csv_table(schedule_path)
            print(f"Using existing schedule: {schedule_path} ({len(schedule)} rows)", flush=True)
        else:
            schedule = collector.schedule(f"{season}-01-01", f"{season}-12-31")
            if args.game_types:
                allowed = {value.strip() for value in args.game_types.split(",") if value.strip()}
                schedule = schedule[schedule["game_type"].isin(allowed)].copy()
            schedule = schedule.dropna(subset=["home_score", "away_score"])
            schedule = schedule.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last")
            write_csv_table(schedule, schedule_path)
            print(f"Wrote schedule: {schedule_path} ({len(schedule)} rows)", flush=True)

        if args.schedule_only:
            continue

        game_ids = schedule["game_id"].dropna().astype(int).astype(str).tolist()
        if args.limit:
            game_ids = game_ids[: args.limit]
        before_existing = len(list(boxscore_dir.glob("*_boxscore.json"))) if boxscore_dir.exists() else 0
        workers = args.workers or default_collection_workers()
        print(f"Collecting {len(game_ids)} boxscores with {workers} workers", flush=True)
        paths = collector.save_boxscores(
            game_ids,
            boxscore_dir,
            skip_existing=True,
            workers=workers,
            progress_callback=_collection_progress(f"Boxscores {season_label}"),
        )
        after_existing = len(list(boxscore_dir.glob("*_boxscore.json")))
        print(
            f"Boxscores ready: {after_existing}/{len(game_ids)} files "
            f"(previously {before_existing})",
            flush=True,
        )
        if args.pause_seconds:
            sleep(args.pause_seconds)

        initial_outputs = standardize_mlb_stats_api_boxscores(
            schedule_csv=schedule_path,
            boxscore_dir=boxscore_dir,
            output_dir=standardized_dir,
            prediction_mode="confirmed_lineup",
        )
        people_inputs = [
            initial_outputs["games"],
            initial_outputs["lineups"],
            initial_outputs["pitcher_logs"],
            initial_outputs["batting_logs"],
        ]
        player_ids: set[int] = set()
        for path in people_inputs:
            frame = read_csv_table(path)
            for column in ["player_id", "home_sp_id", "away_sp_id"]:
                if column in frame.columns:
                    values = pd.to_numeric(frame[column], errors="coerce").dropna().astype(int)
                    player_ids.update(values.tolist())
        if people_path.exists() and not args.refresh_people:
            people = read_csv_table(people_path)
            print(f"Using existing people metadata: {people_path} ({len(people)} rows)", flush=True)
        else:
            people = collector.people(sorted(player_ids))
            write_csv_table(people, people_path)
            print(f"Wrote people metadata: {people_path} ({len(people)} rows)", flush=True)

        standardize_mlb_stats_api_boxscores(
            schedule_csv=schedule_path,
            boxscore_dir=boxscore_dir,
            output_dir=standardized_dir,
            prediction_mode="confirmed_lineup",
            people_csv=people_path,
        )
        builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
        features = builder.build(
            games=read_csv_table(standardized_dir / "games.csv"),
            batting_logs=read_csv_table(standardized_dir / "batting_logs.csv"),
            pitcher_logs=read_csv_table(standardized_dir / "pitcher_logs.csv"),
            lineups=read_csv_table(standardized_dir / "lineups.csv"),
            weather=read_csv_table(standardized_dir / "weather.csv"),
        )
        write_csv_table(features, feature_path)
        print(f"Wrote features: {feature_path} ({features.shape[0]} rows x {features.shape[1]} columns)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(prog="mlb-winprob")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser("build-features")
    _add_common_raw_args(build_parser)
    build_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    build_parser.add_argument("--output", required=True)
    build_parser.set_defaults(func=build_features_command)

    combine_parser = subparsers.add_parser("combine-features")
    combine_parser.add_argument("--inputs", nargs="+", required=True)
    combine_parser.add_argument("--output", required=True)
    combine_parser.set_defaults(func=combine_features_command)

    quality_parser = subparsers.add_parser("feature-quality-report")
    quality_parser.add_argument("--features", nargs="+", required=True)
    quality_parser.add_argument("--output-dir", required=True)
    quality_parser.set_defaults(func=feature_quality_report_command)

    holdout_parser = subparsers.add_parser("season-holdout-report")
    holdout_parser.add_argument("--config", help="TOML config file for a reproducible holdout experiment.")
    holdout_parser.add_argument("--features", nargs="+")
    holdout_parser.add_argument("--output-dir")
    holdout_parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    holdout_parser.add_argument("--models", default="elo,logistic,random_forest")
    holdout_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"])
    holdout_parser.set_defaults(func=season_holdout_report_command)

    expected_runs_parser = subparsers.add_parser("expected-runs-report")
    expected_runs_parser.add_argument("--features", nargs="+", required=True)
    expected_runs_parser.add_argument("--output-dir", required=True)
    expected_runs_parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    expected_runs_parser.add_argument("--models", default="ridge,random_forest_regressor")
    expected_runs_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"])
    expected_runs_parser.add_argument("--synthetic-total-lines", default="6.5,7.5,8.5,9.5,10.5")
    expected_runs_parser.set_defaults(func=expected_runs_report_command)

    park_parser = subparsers.add_parser("build-empirical-park-factors")
    park_parser.add_argument("--standardized-dirs", nargs="+", required=True)
    park_parser.add_argument("--output", required=True)
    park_parser.add_argument("--lag-seasons", type=int, default=1)
    park_parser.add_argument("--min-games", type=int, default=20)
    park_parser.set_defaults(func=build_empirical_park_factors_command)

    train_parser = subparsers.add_parser("train")
    train_parser.add_argument("--features", required=True)
    train_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"])
    train_parser.add_argument("--holdout-season", type=int)
    train_parser.add_argument("--models", help="Comma-separated model names. Defaults to all available models.")
    train_parser.add_argument("--output-dir", required=True)
    train_parser.set_defaults(func=train_command)

    final_model_parser = subparsers.add_parser("fit-final-model")
    final_model_parser.add_argument("--features", required=True)
    final_model_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    final_model_parser.add_argument("--model-name", default="random_forest")
    final_model_parser.add_argument("--random-state", type=int, default=42)
    final_model_parser.add_argument("--output-dir", required=True)
    final_model_parser.set_defaults(func=fit_final_model_command)

    final_runs_parser = subparsers.add_parser("fit-final-runs-model")
    final_runs_parser.add_argument("--features", required=True)
    final_runs_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    final_runs_parser.add_argument("--model-name", choices=["ridge", "random_forest_regressor"], default="random_forest_regressor")
    final_runs_parser.add_argument("--random-state", type=int, default=42)
    final_runs_parser.add_argument("--output-dir", required=True)
    final_runs_parser.set_defaults(func=fit_final_runs_model_command)

    final_ou_parser = subparsers.add_parser("fit-final-ou-model")
    final_ou_parser.add_argument("--features", required=True)
    final_ou_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    final_ou_parser.add_argument("--model-name", default="random_forest")
    final_ou_parser.add_argument("--random-state", type=int, default=42)
    final_ou_parser.add_argument("--total-line", type=float, help="Single baseline over/under line used when features lack market_total_line.")
    final_ou_parser.add_argument("--total-lines", help="CSV with game_id,total_line columns used when features lack market_total_line.")
    final_ou_parser.add_argument("--output-dir", required=True)
    final_ou_parser.set_defaults(func=fit_final_ou_model_command)

    predict_parser = subparsers.add_parser("predict")
    predict_parser.add_argument("--features", required=True)
    predict_parser.add_argument("--model", required=True)
    predict_parser.add_argument("--model-name")
    predict_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    predict_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to predict.")
    predict_parser.set_defaults(func=predict_command)

    predict_runs_parser = subparsers.add_parser("predict-runs")
    predict_runs_parser.add_argument("--features", required=True)
    predict_runs_parser.add_argument("--model", required=True)
    predict_runs_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="pre_lineup")
    predict_runs_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to predict.")
    predict_runs_parser.add_argument("--total-line", type=float, help="Single over/under total line applied to all games.")
    predict_runs_parser.add_argument("--total-lines", help="CSV with game_id,total_line columns.")
    predict_runs_parser.add_argument("--pass-margin", type=float, default=0.5)
    predict_runs_parser.add_argument("--strong-margin", type=float, default=1.5)
    predict_runs_parser.add_argument("--output", help="Optional output CSV. Defaults to JSON lines on stdout.")
    predict_runs_parser.set_defaults(func=predict_runs_command)

    predict_ou_parser = subparsers.add_parser("predict-ou")
    predict_ou_parser.add_argument("--features", required=True)
    predict_ou_parser.add_argument("--model", required=True)
    predict_ou_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="pre_lineup")
    predict_ou_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to predict.")
    predict_ou_parser.add_argument("--total-line", type=float, help="Single over/under total line applied to all games if features lack market_total_line.")
    predict_ou_parser.add_argument("--total-lines", help="CSV with game_id,total_line columns if features lack market_total_line.")
    predict_ou_parser.add_argument("--pass-edge", type=float, default=0.03)
    predict_ou_parser.add_argument("--strong-edge", type=float, default=0.08)
    predict_ou_parser.add_argument("--output", help="Optional output CSV. Defaults to JSON lines on stdout.")
    predict_ou_parser.set_defaults(func=predict_ou_command)

    predict_game_parser = subparsers.add_parser("predict-game")
    predict_game_parser.add_argument("--features", required=True)
    predict_game_parser.add_argument("--win-model", required=True)
    predict_game_parser.add_argument("--runs-model", required=True)
    predict_game_parser.add_argument("--ou-model", help="Optional direct over/under classifier bundle.")
    predict_game_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="pre_lineup")
    predict_game_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to predict.")
    predict_game_parser.add_argument("--total-line", type=float, help="Single over/under total line applied to all games.")
    predict_game_parser.add_argument("--total-lines", help="CSV with game_id,total_line columns.")
    predict_game_parser.add_argument("--pass-margin", type=float, default=0.5)
    predict_game_parser.add_argument("--strong-margin", type=float, default=1.5)
    predict_game_parser.add_argument("--pass-edge", type=float, default=0.03)
    predict_game_parser.add_argument("--strong-edge", type=float, default=0.08)
    predict_game_parser.add_argument("--output", help="Optional output CSV. Defaults to JSON lines on stdout.")
    predict_game_parser.set_defaults(func=predict_game_command)

    win_rules_parser = subparsers.add_parser("win-pick-rule-report")
    win_rules_parser.add_argument("--predictions", required=True, help="CSV with win probabilities and teams.")
    win_rules_parser.add_argument("--output-dir", required=True)
    win_rules_parser.add_argument("--probability-column", default="home_win_probability")
    win_rules_parser.add_argument("--home-team-column", default="home_team")
    win_rules_parser.add_argument("--away-team-column", default="away_team")
    win_rules_parser.add_argument("--actual-winner-column", default="actual_winner")
    win_rules_parser.add_argument("--date-column", default="game_date")
    win_rules_parser.add_argument("--lean-threshold", type=float, default=0.55)
    win_rules_parser.add_argument("--strong-threshold", type=float, default=0.60)
    win_rules_parser.add_argument("--exclude-dates", help="Optional comma-separated YYYY-MM-DD dates to exclude from the report.")
    win_rules_parser.add_argument("--scored-only", action="store_true", help="Compute the overall summary after dropping rows without final scores.")
    win_rules_parser.set_defaults(func=win_pick_rule_report_command)

    oof_selective_parser = subparsers.add_parser("oof-selective-pick-report")
    oof_selective_parser.add_argument("--features", nargs="+", required=True)
    oof_selective_parser.add_argument("--output-dir", required=True)
    oof_selective_parser.add_argument("--holdout-seasons", default="2022,2023,2024,2025")
    oof_selective_parser.add_argument("--models", default="random_forest,random_forest_shallow,soft_voting")
    oof_selective_parser.add_argument("--primary-model", default="random_forest")
    oof_selective_parser.add_argument("--challenger-models", default="random_forest_shallow,soft_voting")
    oof_selective_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    oof_selective_parser.add_argument("--lean-threshold", type=float, default=0.55)
    oof_selective_parser.add_argument("--strong-threshold", type=float, default=0.60)
    oof_selective_parser.add_argument("--random-state", type=int, default=42)
    oof_selective_parser.set_defaults(func=oof_selective_pick_report_command)

    predict_date_parser = subparsers.add_parser("predict-games-by-kst-date")
    predict_date_parser.add_argument("--date-kst", required=True, help="Korea date to predict, e.g. 2026-05-28.")
    predict_date_parser.add_argument("--mlb-date", help="Override MLB schedule date. Defaults to date-kst minus one day.")
    predict_date_parser.add_argument("--output-dir", required=True)
    predict_date_parser.add_argument("--win-model", required=True)
    predict_date_parser.add_argument("--runs-model", required=True)
    predict_date_parser.add_argument("--ou-model")
    predict_date_parser.add_argument("--batting-logs", default="data/standardized/mlb_stats_api_2025/batting_logs.csv")
    predict_date_parser.add_argument("--pitcher-logs", default="data/standardized/mlb_stats_api_2025/pitcher_logs.csv")
    predict_date_parser.add_argument("--season-to-date-standardized", help="Optional standardized season-to-date directory with batting_logs.csv and pitcher_logs.csv.")
    predict_date_parser.add_argument("--park-factors", default="data/processed/park_factors_empirical_previous_season_2022_2026.csv")
    predict_date_parser.add_argument("--venues", default="data/raw/mlb_stats_api/venues_2021_2025.csv")
    predict_date_parser.add_argument("--game-types", default="R")
    predict_date_parser.add_argument("--workers", type=int)
    predict_date_parser.add_argument("--no-skip-existing", action="store_true")
    predict_date_parser.add_argument("--total-line", type=float, default=8.5)
    predict_date_parser.add_argument("--total-lines")
    predict_date_parser.add_argument("--pass-margin", type=float, default=0.5)
    predict_date_parser.add_argument("--strong-margin", type=float, default=1.5)
    predict_date_parser.add_argument("--pass-edge", type=float, default=0.03)
    predict_date_parser.add_argument("--strong-edge", type=float, default=0.08)
    predict_date_parser.add_argument("--lean-threshold", type=float, default=0.55)
    predict_date_parser.add_argument("--strong-threshold", type=float, default=0.60)
    predict_date_parser.add_argument("--ascii-team-names", action="store_true")
    predict_date_parser.set_defaults(func=predict_games_by_kst_date_command)

    review_parser = subparsers.add_parser("review-game-predictions")
    review_parser.add_argument("--predictions", required=True)
    review_parser.add_argument("--output-dir", required=True)
    review_parser.add_argument("--schedule", help="Schedule CSV with final scores. If omitted, --mlb-date is fetched from MLB Stats API.")
    review_parser.add_argument("--mlb-date", help="MLB schedule date to fetch when --schedule is omitted.")
    review_parser.set_defaults(func=review_game_predictions_command)

    season_to_date_parser = subparsers.add_parser("prepare-season-to-date-dataset")
    season_to_date_parser.add_argument("--season", type=int, required=True)
    season_to_date_parser.add_argument("--end-date", required=True, help="Last MLB date to include, e.g. 2026-05-26.")
    season_to_date_parser.add_argument("--start-date", help="Defaults to SEASON-01-01.")
    season_to_date_parser.add_argument("--output-dir", required=True)
    season_to_date_parser.add_argument("--game-types", default="R")
    season_to_date_parser.add_argument("--limit", type=int)
    season_to_date_parser.add_argument("--workers", type=int)
    season_to_date_parser.add_argument("--no-skip-existing", action="store_true")
    season_to_date_parser.set_defaults(func=prepare_season_to_date_dataset_command)

    collect_parser = subparsers.add_parser("collect-statcast")
    collect_parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    collect_parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    collect_parser.add_argument("--output", required=True)
    collect_parser.set_defaults(func=collect_statcast_command)

    statcast_aggregate_parser = subparsers.add_parser("aggregate-statcast")
    statcast_aggregate_parser.add_argument("--statcast", required=True)
    statcast_aggregate_parser.add_argument("--batting-output", required=True)
    statcast_aggregate_parser.add_argument("--pitching-output", required=True)
    statcast_aggregate_parser.set_defaults(func=aggregate_statcast_command)

    statcast_merge_parser = subparsers.add_parser("merge-statcast-logs")
    statcast_merge_parser.add_argument("--batting-logs", required=True)
    statcast_merge_parser.add_argument("--pitcher-logs", required=True)
    statcast_merge_parser.add_argument("--statcast-batting", required=True)
    statcast_merge_parser.add_argument("--statcast-pitching", required=True)
    statcast_merge_parser.add_argument("--batting-output", required=True)
    statcast_merge_parser.add_argument("--pitching-output", required=True)
    statcast_merge_parser.set_defaults(func=merge_statcast_logs_command)

    fangraphs_parser = subparsers.add_parser("collect-fangraphs")
    fangraphs_parser.add_argument("--season", type=int, required=True)
    fangraphs_parser.add_argument("--table", choices=["batting", "pitching"], required=True)
    fangraphs_parser.add_argument("--output", required=True)
    fangraphs_parser.set_defaults(func=collect_fangraphs_command)

    balldontlie_parser = subparsers.add_parser("collect-balldontlie-lineups")
    balldontlie_parser.add_argument("--dates", help="Comma-separated game dates, e.g. 2026-05-26")
    balldontlie_parser.add_argument("--game-ids", help="Comma-separated BALLDONTLIE game ids")
    balldontlie_parser.add_argument("--api-key", help="BALLDONTLIE API key. Defaults to BALLDONTLIE_API_KEY.")
    balldontlie_parser.add_argument("--per-page", type=int, default=100)
    balldontlie_parser.add_argument("--output", required=True)
    balldontlie_parser.set_defaults(func=collect_balldontlie_lineups_command)

    mykbo_parser = subparsers.add_parser("collect-mykbo-season-pages")
    mykbo_parser.add_argument("--start-season", type=int, required=True)
    mykbo_parser.add_argument("--end-season", type=int, required=True)
    mykbo_parser.add_argument("--output-root", default="data")
    mykbo_parser.add_argument(
        "--pages",
        default="stats,batting_ops,pitching_era,team_splits,park_splits,schedule,foreign_players",
        help="Comma-separated MyKBO page keys.",
    )
    mykbo_parser.add_argument("--parse-tables", action="store_true", help="Also parse HTML tables and links into CSV files.")
    mykbo_parser.add_argument("--no-skip-existing", action="store_true")
    mykbo_parser.set_defaults(func=collect_mykbo_season_pages_command)

    mykbo_schedule_parser = subparsers.add_parser("collect-mykbo-schedule-weeks")
    mykbo_schedule_parser.add_argument("--start-date", required=True)
    mykbo_schedule_parser.add_argument("--end-date", required=True)
    mykbo_schedule_parser.add_argument("--output-root", default="data")
    mykbo_schedule_parser.add_argument("--parse-tables", action="store_true", help="Also parse schedule links/text into CSV files.")
    mykbo_schedule_parser.add_argument("--no-skip-existing", action="store_true")
    mykbo_schedule_parser.set_defaults(func=collect_mykbo_schedule_weeks_command)

    mykbo_games_parser = subparsers.add_parser("collect-mykbo-game-pages")
    mykbo_games_parser.add_argument("--games", required=True, help="CSV from standardize-mykbo-schedule")
    mykbo_games_parser.add_argument("--output-dir", required=True)
    mykbo_games_parser.add_argument("--limit", type=int)
    mykbo_games_parser.add_argument("--final-only", action="store_true")
    mykbo_games_parser.add_argument("--parse-tables", action="store_true")
    mykbo_games_parser.add_argument("--parsed-dir")
    mykbo_games_parser.add_argument("--no-skip-existing", action="store_true")
    mykbo_games_parser.add_argument("--delay", type=float, default=1.0, help="Base seconds to wait between requests (jittered).")
    mykbo_games_parser.add_argument("--workers", type=int, default=1, help="Parallel fetch workers.")
    mykbo_games_parser.set_defaults(func=collect_mykbo_game_pages_command)

    mykbo_standardize_parser = subparsers.add_parser("standardize-mykbo-tables")
    mykbo_standardize_parser.add_argument("--season", type=int, required=True)
    mykbo_standardize_parser.add_argument("--input-dir", required=True)
    mykbo_standardize_parser.add_argument("--output-dir", required=True)
    mykbo_standardize_parser.set_defaults(func=standardize_mykbo_tables_command)

    mykbo_schedule_standardize_parser = subparsers.add_parser("standardize-mykbo-schedule")
    mykbo_schedule_standardize_parser.add_argument("--input-dir", required=True)
    mykbo_schedule_standardize_parser.add_argument("--output", required=True)
    mykbo_schedule_standardize_parser.set_defaults(func=standardize_mykbo_schedule_command)

    mykbo_game_standardize_parser = subparsers.add_parser("standardize-mykbo-game-tables")
    mykbo_game_standardize_parser.add_argument("--input-dir", required=True)
    mykbo_game_standardize_parser.add_argument("--games", required=True)
    mykbo_game_standardize_parser.add_argument("--output-dir", required=True)
    mykbo_game_standardize_parser.set_defaults(func=standardize_mykbo_game_tables_command)

    balldontlie_standardize_parser = subparsers.add_parser("standardize-balldontlie-lineups")
    balldontlie_standardize_parser.add_argument("--input", required=True, help="Raw JSON from collect-balldontlie-lineups")
    balldontlie_standardize_parser.add_argument("--output", required=True)
    balldontlie_standardize_parser.add_argument("--prediction-mode", choices=["pre_lineup", "projected", "expected"], default="projected")
    balldontlie_standardize_parser.add_argument("--captured-at", help="Snapshot timestamp available before first pitch.")
    balldontlie_standardize_parser.add_argument("--game-id-map", help="CSV with external_game_id,game_id columns.")
    balldontlie_standardize_parser.add_argument("--player-id-map", help="CSV with external_player_id,player_id columns.")
    balldontlie_standardize_parser.set_defaults(func=standardize_balldontlie_lineups_command)

    manual_template_parser = subparsers.add_parser("write-manual-lineup-template")
    manual_template_parser.add_argument("--games", required=True, help="Project-standard games.csv.")
    manual_template_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to include.")
    manual_template_parser.add_argument("--output", required=True)
    manual_template_parser.set_defaults(func=write_manual_lineup_template_command)

    market_template_parser = subparsers.add_parser("write-market-lines-template")
    market_template_parser.add_argument("--games", required=True, help="Project-standard games.csv.")
    market_template_parser.add_argument("--game-ids", help="Optional comma-separated game IDs to include.")
    market_template_parser.add_argument("--output", required=True)
    market_template_parser.set_defaults(func=write_market_lines_template_command)

    manual_standardize_parser = subparsers.add_parser("standardize-manual-lineups")
    manual_standardize_parser.add_argument("--input", required=True, help="User-edited manual lineup CSV.")
    manual_standardize_parser.add_argument("--output", required=True)
    manual_standardize_parser.add_argument("--id-map", help="Optional project id_map.csv for player_name -> player_id.")
    manual_standardize_parser.add_argument("--season", type=int, help="Optional season filter for player name matching.")
    manual_standardize_parser.add_argument("--prediction-mode", choices=["pre_lineup", "projected", "expected"], default="projected")
    manual_standardize_parser.add_argument("--lineup-source", default="manual")
    manual_standardize_parser.add_argument("--captured-at", help="Manual snapshot timestamp.")
    manual_standardize_parser.set_defaults(func=standardize_manual_lineups_command)

    schedule_parser = subparsers.add_parser("collect-mlb-schedule")
    schedule_parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    schedule_parser.add_argument("--end-date", required=True, help="YYYY-MM-DD")
    schedule_parser.add_argument("--sport-id", type=int, default=1)
    schedule_parser.add_argument("--hydrate", default="probablePitcher,venue,team,linescore")
    schedule_parser.add_argument("--output", required=True)
    schedule_parser.set_defaults(func=collect_mlb_schedule_command)

    boxscore_parser = subparsers.add_parser("collect-mlb-boxscores")
    boxscore_parser.add_argument("--games", required=True, help="CSV from collect-mlb-schedule")
    boxscore_parser.add_argument("--output-dir", required=True)
    boxscore_parser.add_argument("--limit", type=int)
    boxscore_parser.add_argument("--workers", type=int, help="Parallel workers. Defaults to min(32, CPU count * 2).")
    boxscore_parser.add_argument("--no-skip-existing", action="store_true")
    boxscore_parser.set_defaults(func=collect_mlb_boxscores_command)

    lineup_snapshot_parser = subparsers.add_parser("collect-mlb-lineup-snapshots")
    lineup_snapshot_parser.add_argument("--games", required=True, help="CSV from collect-mlb-schedule")
    lineup_snapshot_parser.add_argument("--output-dir", required=True)
    lineup_snapshot_parser.add_argument("--manifest", help="Optional CSV recording game_id, snapshot path, captured_at.")
    lineup_snapshot_parser.add_argument("--captured-at", help="Override snapshot timestamp. Defaults to current UTC time.")
    lineup_snapshot_parser.add_argument("--limit", type=int)
    lineup_snapshot_parser.add_argument("--workers", type=int, help="Parallel workers. Defaults to min(32, CPU count * 2).")
    lineup_snapshot_parser.add_argument("--no-skip-existing", action="store_true")
    lineup_snapshot_parser.set_defaults(func=collect_mlb_lineup_snapshots_command)

    feed_parser = subparsers.add_parser("collect-mlb-feeds")
    feed_parser.add_argument("--games", required=True, help="CSV from collect-mlb-schedule")
    feed_parser.add_argument("--output-dir", required=True)
    feed_parser.add_argument("--limit", type=int)
    feed_parser.add_argument("--workers", type=int, help="Parallel workers. Defaults to min(32, CPU count * 2).")
    feed_parser.add_argument("--no-skip-existing", action="store_true")
    feed_parser.set_defaults(func=collect_mlb_feeds_command)

    people_parser = subparsers.add_parser("collect-mlb-people")
    people_parser.add_argument("--inputs", nargs="+", required=True, help="CSV files containing MLBAM player id columns")
    people_parser.add_argument(
        "--id-columns",
        default="player_id,home_sp_id,away_sp_id",
        help="Comma-separated columns to scan for MLBAM player ids",
    )
    people_parser.add_argument("--output", required=True)
    people_parser.set_defaults(func=collect_mlb_people_command)

    venues_parser = subparsers.add_parser("collect-mlb-venues")
    venues_parser.add_argument("--inputs", nargs="+", required=True, help="CSV files containing venue_id columns")
    venues_parser.add_argument("--output", required=True)
    venues_parser.set_defaults(func=collect_mlb_venues_command)

    openmeteo_parser = subparsers.add_parser("augment-weather-openmeteo")
    openmeteo_parser.add_argument("--games", required=True)
    openmeteo_parser.add_argument("--weather", required=True)
    openmeteo_parser.add_argument("--venues", required=True)
    openmeteo_parser.add_argument("--output", required=True)
    openmeteo_parser.set_defaults(func=augment_weather_openmeteo_command)

    retrosheet_parser = subparsers.add_parser("collect-retrosheet")
    retrosheet_parser.add_argument(
        "--dataset",
        choices=sorted(RetrosheetCollector.downloads),
        required=True,
    )
    retrosheet_parser.add_argument("--output", required=True)
    retrosheet_parser.set_defaults(func=collect_retrosheet_command)

    lahman_parser = subparsers.add_parser("collect-lahman")
    lahman_parser.add_argument("--table", default="People")
    lahman_parser.add_argument("--archive", action="store_true")
    lahman_parser.add_argument("--output", required=True)
    lahman_parser.set_defaults(func=collect_lahman_command)

    chadwick_parser = subparsers.add_parser("collect-chadwick-people")
    chadwick_parser.add_argument("--output", required=True)
    chadwick_parser.set_defaults(func=collect_chadwick_people_command)

    id_map_parser = subparsers.add_parser("build-id-map")
    id_map_parser.add_argument("--chadwick-people", required=True)
    id_map_parser.add_argument("--mlb-people", nargs="*", help="Optional MLB Stats API people metadata CSV files")
    id_map_parser.add_argument("--output", required=True)
    id_map_parser.set_defaults(func=build_id_map_command)

    external_id_map_parser = subparsers.add_parser("build-external-lineup-id-maps")
    external_id_map_parser.add_argument("--provider-lineups", required=True, help="Normalized provider lineups CSV.")
    external_id_map_parser.add_argument("--mlb-games", help="Project-standard games.csv for game ID mapping.")
    external_id_map_parser.add_argument("--id-map", help="Project id_map.csv for player ID mapping.")
    external_id_map_parser.add_argument("--season", type=int, help="Optional active MLB season filter for player name matching.")
    external_id_map_parser.add_argument("--game-map-output", help="Output CSV with external_game_id,game_id.")
    external_id_map_parser.add_argument("--player-map-output", help="Output CSV with external_player_id,player_id.")
    external_id_map_parser.set_defaults(func=build_external_lineup_id_maps_command)

    url_parser = subparsers.add_parser("download-url")
    url_parser.add_argument("--url", required=True)
    url_parser.add_argument("--output", required=True)
    url_parser.set_defaults(func=download_url_command)

    standardize_parser = subparsers.add_parser("standardize-mlb-boxscores")
    standardize_parser.add_argument("--schedule", required=True)
    standardize_parser.add_argument("--boxscore-dir", required=True)
    standardize_parser.add_argument("--output-dir", required=True)
    standardize_parser.add_argument("--prediction-mode", choices=["pre_lineup", "confirmed_lineup"], default="confirmed_lineup")
    standardize_parser.add_argument("--people", help="Optional MLB Stats API people metadata CSV")
    standardize_parser.add_argument("--lineup-source", help="Optional lineup_source value for standardized lineups.")
    standardize_parser.add_argument("--captured-at", help="Optional snapshot timestamp for standardized lineups.")
    standardize_parser.add_argument("--lineup-confidence", type=float, help="Optional lineup confidence for standardized lineups.")
    standardize_parser.set_defaults(func=standardize_mlb_boxscores_command)

    retrosheet_standardize_parser = subparsers.add_parser("standardize-retrosheet")
    retrosheet_standardize_parser.add_argument("--gameinfo", required=True)
    retrosheet_standardize_parser.add_argument("--teamstats", required=True)
    retrosheet_standardize_parser.add_argument("--batting", required=True)
    retrosheet_standardize_parser.add_argument("--pitching", required=True)
    retrosheet_standardize_parser.add_argument("--output-dir", required=True)
    retrosheet_standardize_parser.add_argument("--seasons", help="Comma-separated seasons to include, e.g. 2021,2022")
    retrosheet_standardize_parser.set_defaults(func=standardize_retrosheet_command)

    season_dataset_parser = subparsers.add_parser("collect-mlb-season-dataset")
    season_dataset_parser.add_argument("--start-season", type=int, required=True)
    season_dataset_parser.add_argument("--end-season", type=int, required=True)
    season_dataset_parser.add_argument("--output-root", default="data")
    season_dataset_parser.add_argument("--game-types", default="R", help="Comma-separated game types, e.g. R or R,F,D,L,W")
    season_dataset_parser.add_argument("--limit", type=int, help="Limit games per season for smoke tests")
    season_dataset_parser.add_argument("--schedule-only", action="store_true")
    season_dataset_parser.add_argument("--refresh-schedule", action="store_true")
    season_dataset_parser.add_argument("--refresh-people", action="store_true")
    season_dataset_parser.add_argument("--pause-seconds", type=float, default=0.0)
    season_dataset_parser.add_argument("--workers", type=int, help="Parallel boxscore workers. Defaults to min(32, CPU count * 2).")
    season_dataset_parser.set_defaults(func=collect_mlb_season_dataset_command)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
