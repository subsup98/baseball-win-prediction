"""Shared column names and feature conventions."""

TARGET_COLUMN = "home_team_win"

PREDICTION_MODES = {"pre_lineup", "confirmed_lineup"}

NON_FEATURE_COLUMNS = {
    "game_id",
    "game_date",
    "season",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "actual_total",
    "home_sp_id",
    "away_sp_id",
    "venue_id",
    "prediction_mode",
    "market_closing_total_line",
    "market_total_over",
    TARGET_COLUMN,
}

CONFIDENCE_THRESHOLDS = (0.55, 0.60, 0.65)
