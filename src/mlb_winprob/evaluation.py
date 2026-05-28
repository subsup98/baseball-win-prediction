"""Model evaluation utilities."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss

from mlb_winprob.constants import CONFIDENCE_THRESHOLDS, TARGET_COLUMN


def evaluate_probabilities(
    y_true: pd.Series | np.ndarray,
    home_win_probability: pd.Series | np.ndarray,
    *,
    confidence_thresholds: tuple[float, ...] = CONFIDENCE_THRESHOLDS,
) -> dict[str, float]:
    y = np.asarray(y_true, dtype=int)
    probabilities = np.clip(np.asarray(home_win_probability, dtype=float), 1e-6, 1 - 1e-6)
    predictions = (probabilities >= 0.5).astype(int)
    metrics: dict[str, float] = {
        "log_loss": float(log_loss(y, probabilities, labels=[0, 1])),
        "brier_score": float(brier_score_loss(y, probabilities)),
        "accuracy": float(accuracy_score(y, predictions)),
        "n_games": float(len(y)),
    }

    confidence = np.maximum(probabilities, 1 - probabilities)
    for threshold in confidence_thresholds:
        mask = confidence >= threshold
        key = f"accuracy_conf_{int(threshold * 100)}"
        coverage_key = f"coverage_conf_{int(threshold * 100)}"
        metrics[key] = float(accuracy_score(y[mask], predictions[mask])) if mask.any() else np.nan
        metrics[coverage_key] = float(mask.mean())
    return metrics


def calibration_table(
    y_true: pd.Series | np.ndarray,
    home_win_probability: pd.Series | np.ndarray,
    *,
    bins: int = 10,
) -> pd.DataFrame:
    frame = pd.DataFrame(
        {
            "y_true": np.asarray(y_true, dtype=int),
            "probability": np.asarray(home_win_probability, dtype=float),
        }
    )
    frame["bin"] = pd.cut(frame["probability"], bins=np.linspace(0, 1, bins + 1), include_lowest=True)
    table = (
        frame.groupby("bin", observed=False)
        .agg(
            n_games=("y_true", "size"),
            predicted_home_win_rate=("probability", "mean"),
            actual_home_win_rate=("y_true", "mean"),
        )
        .reset_index()
    )
    table["calibration_error"] = table["predicted_home_win_rate"] - table["actual_home_win_rate"]
    return table


def model_selection_rules(
    metrics: pd.DataFrame,
    *,
    confidence_thresholds: tuple[float, ...] = CONFIDENCE_THRESHOLDS,
    min_coverage: float = 0.10,
) -> pd.DataFrame:
    """Choose simple per-holdout model rules from existing metrics.

    The output is intentionally rule-based and auditable: one overall log-loss
    winner plus optional confidence-band winners when coverage is high enough.
    """

    if metrics.empty:
        return pd.DataFrame()
    required = {"holdout_season", "model_name", "log_loss", "brier_score"}
    missing = required - set(metrics.columns)
    if missing:
        raise ValueError(f"metrics is missing required columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for season, group in metrics.groupby("holdout_season", sort=True):
        overall = group.sort_values(["log_loss", "brier_score", "model_name"]).iloc[0]
        rows.append(
            {
                "holdout_season": season,
                "rule_name": "overall_log_loss",
                "selected_model": overall["model_name"],
                "selection_metric": "log_loss",
                "selection_value": float(overall["log_loss"]),
                "coverage": 1.0,
            }
        )
        for threshold in confidence_thresholds:
            suffix = int(threshold * 100)
            accuracy_column = f"accuracy_conf_{suffix}"
            coverage_column = f"coverage_conf_{suffix}"
            if accuracy_column not in group.columns or coverage_column not in group.columns:
                continue
            eligible = group[group[coverage_column].fillna(0) >= min_coverage].copy()
            eligible = eligible.dropna(subset=[accuracy_column])
            if eligible.empty:
                continue
            selected = eligible.sort_values(
                [accuracy_column, coverage_column, "log_loss", "model_name"],
                ascending=[False, False, True, True],
            ).iloc[0]
            rows.append(
                {
                    "holdout_season": season,
                    "rule_name": f"confidence_{suffix}",
                    "selected_model": selected["model_name"],
                    "selection_metric": accuracy_column,
                    "selection_value": float(selected[accuracy_column]),
                    "coverage": float(selected[coverage_column]),
                }
            )
    return pd.DataFrame(rows)


def apply_win_pick_rules(
    predictions: pd.DataFrame,
    *,
    probability_column: str = "home_win_probability",
    home_team_column: str = "home_team",
    away_team_column: str = "away_team",
    actual_winner_column: str = "actual_winner",
    lean_threshold: float = 0.55,
    strong_threshold: float = 0.60,
) -> pd.DataFrame:
    """Add pass/lean/strong win-pick rules to a prediction table."""

    if lean_threshold < 0.5:
        raise ValueError("lean_threshold must be at least 0.5")
    if strong_threshold < lean_threshold:
        raise ValueError("strong_threshold must be greater than or equal to lean_threshold")
    required = {probability_column, home_team_column, away_team_column}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"predictions is missing required columns: {sorted(missing)}")

    output = predictions.copy()
    probabilities = pd.to_numeric(output[probability_column], errors="coerce")
    output["win_confidence"] = np.maximum(probabilities, 1 - probabilities)
    output["win_edge"] = output["win_confidence"] - 0.5
    output["raw_win_pick"] = np.where(
        probabilities >= 0.5,
        output[home_team_column].astype(str),
        output[away_team_column].astype(str),
    )
    output["win_pick_rule"] = np.select(
        [
            output["win_confidence"] >= strong_threshold,
            output["win_confidence"] >= lean_threshold,
        ],
        ["strong", "lean"],
        default="pass",
    )
    output["rule_win_pick"] = np.where(output["win_pick_rule"].eq("pass"), "", output["raw_win_pick"])

    if actual_winner_column in output.columns:
        actual_winner = output[actual_winner_column]
        scored = actual_winner.notna() & actual_winner.astype(str).str.strip().ne("")
        output["rule_win_correct"] = np.where(
            output["win_pick_rule"].eq("pass") | ~scored,
            np.nan,
            output["rule_win_pick"].astype(str).eq(actual_winner.astype(str)),
        )
    return output


def summarize_win_pick_rules(
    predictions: pd.DataFrame,
    *,
    rule_column: str = "win_pick_rule",
    correct_column: str = "rule_win_correct",
    confidence_column: str = "win_confidence",
) -> pd.DataFrame:
    """Summarize pass/lean/strong rule coverage and hit rate."""

    if rule_column not in predictions.columns:
        raise ValueError(f"predictions must include {rule_column}")

    rows: list[dict[str, object]] = []
    ordered_rules = ["pass", "lean", "strong"]
    for rule in ordered_rules:
        group = predictions[predictions[rule_column].eq(rule)]
        actionable = group[~group[correct_column].isna()] if correct_column in group.columns else group.iloc[0:0]
        hits = float(actionable[correct_column].astype(bool).sum()) if correct_column in group.columns else np.nan
        picks = int(len(actionable)) if correct_column in group.columns else int(len(group))
        rows.append(
            {
                "rule": rule,
                "games": int(len(group)),
                "picks": picks,
                "hits": hits if not np.isnan(hits) else np.nan,
                "accuracy": float(hits / picks) if picks else np.nan,
                "coverage": float(len(group) / len(predictions)) if len(predictions) else np.nan,
                "avg_confidence": float(group[confidence_column].mean()) if confidence_column in group.columns and not group.empty else np.nan,
            }
        )

    actionable_all = predictions[predictions[rule_column].ne("pass")]
    if correct_column in actionable_all.columns:
        scored = actionable_all[~actionable_all[correct_column].isna()]
        hits = float(scored[correct_column].astype(bool).sum())
        picks = int(len(scored))
    else:
        hits = np.nan
        picks = int(len(actionable_all))
    rows.append(
        {
            "rule": "actionable",
            "games": int(len(actionable_all)),
            "picks": picks,
            "hits": hits,
            "accuracy": float(hits / picks) if picks else np.nan,
            "coverage": float(len(actionable_all) / len(predictions)) if len(predictions) else np.nan,
            "avg_confidence": float(actionable_all[confidence_column].mean())
            if confidence_column in actionable_all.columns and not actionable_all.empty
            else np.nan,
        }
    )
    return pd.DataFrame(rows)


def apply_ou_pick_rules(
    predictions: pd.DataFrame,
    *,
    predicted_total_column: str = "pred_total",
    total_line_column: str = "total_line",
    actual_total_column: str = "actual_total",
    lean_margin: float = 0.5,
    strong_margin: float = 1.5,
) -> pd.DataFrame:
    """Add pass/lean/strong over-under pick rules to a prediction table.

    Mirrors :func:`apply_win_pick_rules` but for totals: the "confidence" is the
    absolute distance between the predicted total and the market line. A pick is
    `pass` below ``lean_margin``, `lean` at/above it, and `strong` at/above
    ``strong_margin``.
    """

    if lean_margin < 0:
        raise ValueError("lean_margin must be non-negative")
    if strong_margin < lean_margin:
        raise ValueError("strong_margin must be greater than or equal to lean_margin")
    required = {predicted_total_column, total_line_column}
    missing = required - set(predictions.columns)
    if missing:
        raise ValueError(f"predictions is missing required columns: {sorted(missing)}")

    output = predictions.copy()
    predicted_total = pd.to_numeric(output[predicted_total_column], errors="coerce")
    total_line = pd.to_numeric(output[total_line_column], errors="coerce")
    output["ou_margin"] = predicted_total - total_line
    output["ou_confidence"] = output["ou_margin"].abs()
    output["raw_ou_pick"] = np.where(output["ou_margin"] > 0, "over", "under")
    output["ou_pick_rule"] = np.select(
        [
            output["ou_confidence"] >= strong_margin,
            output["ou_confidence"] >= lean_margin,
        ],
        ["strong", "lean"],
        default="pass",
    )
    # Rows without a usable margin (missing prediction or line) are forced to pass.
    output.loc[output["ou_margin"].isna(), "ou_pick_rule"] = "pass"
    output["rule_ou_pick"] = np.where(output["ou_pick_rule"].eq("pass"), "", output["raw_ou_pick"])

    if actual_total_column in output.columns:
        actual_total = pd.to_numeric(output[actual_total_column], errors="coerce")
        scored = actual_total.notna() & total_line.notna()
        output["actual_ou"] = np.where(
            scored,
            np.where(actual_total > total_line, "over", "under"),
            "",
        )
        output["rule_ou_correct"] = np.where(
            output["ou_pick_rule"].eq("pass") | ~scored,
            np.nan,
            output["rule_ou_pick"].astype(str).eq(pd.Series(output["actual_ou"], index=output.index).astype(str)),
        )
    return output


def summarize_ou_pick_rules(
    predictions: pd.DataFrame,
    *,
    rule_column: str = "ou_pick_rule",
    correct_column: str = "rule_ou_correct",
    margin_column: str = "ou_confidence",
) -> pd.DataFrame:
    """Summarize pass/lean/strong over-under rule coverage and hit rate."""

    if rule_column not in predictions.columns:
        raise ValueError(f"predictions must include {rule_column}")

    def _row(label: str, group: pd.DataFrame) -> dict[str, object]:
        if correct_column in group.columns:
            scored = group[~group[correct_column].isna()]
            hits = float(scored[correct_column].astype(bool).sum())
            picks = int(len(scored))
        else:
            hits = np.nan
            picks = int(len(group))
        return {
            "rule": label,
            "games": int(len(group)),
            "picks": picks,
            "hits": hits,
            "accuracy": float(hits / picks) if picks else np.nan,
            "coverage": float(len(group) / len(predictions)) if len(predictions) else np.nan,
            "avg_margin": float(group[margin_column].mean())
            if margin_column in group.columns and not group.empty
            else np.nan,
        }

    rows = [_row(rule, predictions[predictions[rule_column].eq(rule)]) for rule in ["pass", "lean", "strong"]]
    rows.append(_row("actionable", predictions[predictions[rule_column].ne("pass")]))
    return pd.DataFrame(rows)


def apply_model_agreement_pick_rules(
    oof_predictions: pd.DataFrame,
    *,
    primary_model: str,
    challenger_models: list[str],
    lean_threshold: float = 0.55,
    strong_threshold: float = 0.60,
) -> pd.DataFrame:
    """Apply pass/lean/strong rules only when challenger models agree with the primary pick."""

    required = {"model_name", "home_win_probability", "home_team", "away_team"}
    missing = required - set(oof_predictions.columns)
    if missing:
        raise ValueError(f"oof_predictions is missing required columns: {sorted(missing)}")

    primary = oof_predictions[oof_predictions["model_name"].astype(str).eq(primary_model)].copy()
    if primary.empty:
        raise ValueError(f"primary_model {primary_model!r} is not present in oof_predictions")
    primary = apply_win_pick_rules(primary, lean_threshold=lean_threshold, strong_threshold=strong_threshold)

    merge_keys = [column for column in ["holdout_season", "game_id"] if column in primary.columns]
    if "game_id" not in merge_keys:
        merge_keys = [column for column in ["holdout_season", "game_date", "home_team", "away_team"] if column in primary.columns]
    if not merge_keys:
        raise ValueError("oof_predictions must include game_id or enough game identity columns for agreement matching")

    output = primary.copy()
    agreement_columns: list[str] = []
    for challenger in challenger_models:
        challenger_frame = oof_predictions[oof_predictions["model_name"].astype(str).eq(challenger)].copy()
        if challenger_frame.empty:
            continue
        challenger_frame = apply_win_pick_rules(challenger_frame, lean_threshold=lean_threshold, strong_threshold=strong_threshold)
        columns = merge_keys + ["raw_win_pick", "win_confidence"]
        suffix = challenger.replace("/", "_")
        challenger_frame = challenger_frame[columns].rename(
            columns={
                "raw_win_pick": f"{suffix}_raw_win_pick",
                "win_confidence": f"{suffix}_win_confidence",
            }
        )
        output = output.merge(challenger_frame, on=merge_keys, how="left")
        agree_column = f"{suffix}_agrees"
        output[agree_column] = output[f"{suffix}_raw_win_pick"].astype(str).eq(output["raw_win_pick"].astype(str))
        agreement_columns.append(agree_column)

    if agreement_columns:
        output["agreement_models"] = output[agreement_columns].sum(axis=1).astype(int)
        output["agreement_required"] = len(agreement_columns)
        output["models_agree"] = output[agreement_columns].all(axis=1)
    else:
        output["agreement_models"] = 0
        output["agreement_required"] = 0
        output["models_agree"] = True

    output["win_pick_rule"] = np.where(output["models_agree"], output["win_pick_rule"], "pass")
    output["rule_win_pick"] = np.where(output["win_pick_rule"].eq("pass"), "", output["raw_win_pick"])
    if "actual_winner" in output.columns:
        output["rule_win_correct"] = np.where(
            output["win_pick_rule"].eq("pass"),
            np.nan,
            output["rule_win_pick"].astype(str).eq(output["actual_winner"].astype(str)),
        )
    return output


def temporal_train_test_split(
    features: pd.DataFrame,
    *,
    test_fraction: float = 0.2,
    date_column: str = "game_date",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if TARGET_COLUMN not in features.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")
    frame = features.dropna(subset=[TARGET_COLUMN]).copy()
    frame[date_column] = pd.to_datetime(frame[date_column])
    frame = frame.sort_values([date_column, "game_id"]).reset_index(drop=True)
    split_index = max(1, int(len(frame) * (1 - test_fraction)))
    return frame.iloc[:split_index].copy(), frame.iloc[split_index:].copy()


def season_holdout_split(
    features: pd.DataFrame,
    *,
    holdout_season: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if TARGET_COLUMN not in features.columns:
        raise ValueError(f"features must include {TARGET_COLUMN}")
    frame = features.dropna(subset=[TARGET_COLUMN]).copy()
    if holdout_season is None:
        holdout_season = int(frame["season"].max())
    train = frame[frame["season"] < holdout_season].copy()
    test = frame[frame["season"] == holdout_season].copy()
    if train.empty or test.empty:
        return temporal_train_test_split(frame)
    return train, test
