"""Leakage-safe game-level feature generation.

The builder accepts raw game, batting, pitching, lineup, weather, and park-factor
tables and returns one row per game. Every rolling and season-to-date statistic
uses only rows before the target game.
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from mlb_winprob.constants import PREDICTION_MODES, TARGET_COLUMN
from mlb_winprob.schemas import FeatureBuildConfig

BATTING_STATS = [
    "at_bats",
    "hits",
    "doubles",
    "triples",
    "home_runs",
    "walks",
    "hit_by_pitch",
    "sacrifice_flies",
    "total_bases",
    "plate_appearances",
]

PITCHING_STATS = [
    "innings_pitched",
    "hits",
    "home_runs",
    "walks",
    "hit_by_pitch",
    "strikeouts",
    "batters_faced",
    "pitches",
]

BATTING_STATCAST_SUMS = [
    "statcast_pa",
    "statcast_batted_balls",
    "statcast_hard_hit_balls",
    "statcast_barrels",
    "statcast_xwoba_sum",
    "statcast_xwoba_count",
    "statcast_woba_sum",
    "statcast_woba_count",
    "statcast_launch_speed_sum",
]

PITCHING_STATCAST_SUMS = [
    "statcast_batters_faced",
    "statcast_batted_balls_allowed",
    "statcast_hard_hit_balls_allowed",
    "statcast_barrels_allowed",
    "statcast_xwoba_allowed_sum",
    "statcast_xwoba_allowed_count",
    "statcast_woba_allowed_sum",
    "statcast_woba_allowed_count",
    "statcast_launch_speed_allowed_sum",
]

WEATHER_COLUMNS = ["temperature", "wind_speed", "wind_direction", "humidity", "is_dome"]
PARK_FACTOR_COLUMNS = ["park_factor_run", "park_factor_hr"]


def _safe_divide(numerator: pd.Series | np.ndarray, denominator: pd.Series | np.ndarray) -> np.ndarray:
    numerator_arr = np.asarray(numerator, dtype=float)
    denominator_arr = np.asarray(denominator, dtype=float)
    return np.divide(
        numerator_arr,
        denominator_arr,
        out=np.full_like(numerator_arr, np.nan, dtype=float),
        where=denominator_arr > 0,
    )


def _require_columns(frame: pd.DataFrame, columns: Iterable[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"{name} is missing required columns: {missing}")


def _with_datetime(frame: pd.DataFrame, column: str = "game_date") -> pd.DataFrame:
    out = frame.copy()
    if column in out.columns:
        out[column] = pd.to_datetime(out[column])
    return out


def _ensure_numeric_columns(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    out = frame.copy()
    for column in columns:
        if column not in out.columns:
            out[column] = 0.0
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
    return out


def _batting_rates_from_columns(frame: pd.DataFrame, suffix: str = "") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    at_bats = frame[f"at_bats{suffix}"]
    hits = frame[f"hits{suffix}"]
    doubles = frame[f"doubles{suffix}"]
    triples = frame[f"triples{suffix}"]
    home_runs = frame[f"home_runs{suffix}"]
    walks = frame[f"walks{suffix}"]
    hbp = frame[f"hit_by_pitch{suffix}"]
    sacrifice_flies = frame[f"sacrifice_flies{suffix}"]
    total_bases = frame[f"total_bases{suffix}"]

    singles = (hits - doubles - triples - home_runs).clip(lower=0)
    obp = _safe_divide(hits + walks + hbp, at_bats + walks + hbp + sacrifice_flies)
    slg = _safe_divide(total_bases, at_bats)
    ops = obp + slg
    woba = _safe_divide(
        0.69 * walks + 0.72 * hbp + 0.89 * singles + 1.27 * doubles + 1.62 * triples + 2.10 * home_runs,
        at_bats + walks + hbp + sacrifice_flies,
    )
    iso = _safe_divide(total_bases - hits, at_bats)
    return ops, woba, iso


def _pitching_fip(
    innings: pd.Series,
    home_runs: pd.Series,
    walks: pd.Series,
    hit_by_pitch: pd.Series,
    strikeouts: pd.Series,
    fip_constant: float,
) -> np.ndarray:
    return _safe_divide(13 * home_runs + 3 * (walks + hit_by_pitch) - 2 * strikeouts, innings) + fip_constant


def _team_game_rows(games: pd.DataFrame) -> pd.DataFrame:
    _require_columns(
        games,
        ["game_id", "game_date", "season", "home_team", "away_team"],
        "games",
    )
    games = games.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last").copy()
    home = games[["game_id", "game_date", "season", "home_team", "away_team"]].copy()
    home = home.rename(columns={"home_team": "team", "away_team": "opponent"})
    home["is_home"] = 1
    away = games[["game_id", "game_date", "season", "away_team", "home_team"]].copy()
    away = away.rename(columns={"away_team": "team", "home_team": "opponent"})
    away["is_home"] = 0
    rows = pd.concat([home, away], ignore_index=True)

    if {"home_score", "away_score"}.issubset(games.columns):
        scores = games[["game_id", "home_score", "away_score"]].copy()
        rows = rows.merge(scores, on="game_id", how="left")
        rows["runs_for"] = np.where(rows["is_home"] == 1, rows["home_score"], rows["away_score"])
        rows["runs_allowed"] = np.where(rows["is_home"] == 1, rows["away_score"], rows["home_score"])
        rows["win"] = np.where(rows["runs_for"].notna() & rows["runs_allowed"].notna(), rows["runs_for"] > rows["runs_allowed"], np.nan)
        rows["win"] = rows["win"].astype(float)
        rows = rows.drop(columns=["home_score", "away_score"])
    else:
        rows["runs_for"] = np.nan
        rows["runs_allowed"] = np.nan
        rows["win"] = np.nan

    return rows.sort_values(["team", "season", "game_date", "game_id"]).reset_index(drop=True)


def _rolling_sum_before_dates(group: pd.DataFrame, value_column: str, days: int) -> pd.Series:
    values: list[float] = []
    dates = group["game_date"].reset_index(drop=True)
    raw = group[value_column].fillna(0).reset_index(drop=True)
    for index, current_date in enumerate(dates):
        start = current_date - pd.Timedelta(days=days)
        mask = (dates >= start) & (dates < current_date)
        values.append(float(raw.loc[mask].sum()))
    return pd.Series(values, index=group.index)


class FeatureBuilder:
    """Build one leakage-safe row per MLB game."""

    def __init__(self, config: FeatureBuildConfig | None = None) -> None:
        self.config = config or FeatureBuildConfig()
        if self.config.prediction_mode not in PREDICTION_MODES:
            raise ValueError(f"prediction_mode must be one of {sorted(PREDICTION_MODES)}")

    def build(
        self,
        *,
        games: pd.DataFrame,
        batting_logs: pd.DataFrame,
        pitcher_logs: pd.DataFrame,
        lineups: pd.DataFrame,
        weather: pd.DataFrame | None = None,
        park_factors: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        games = _with_datetime(games)
        batting_logs = _with_datetime(batting_logs)
        pitcher_logs = _with_datetime(pitcher_logs)
        lineups = lineups.copy()

        _require_columns(
            games,
            ["game_id", "game_date", "season", "home_team", "away_team", "home_sp_id", "away_sp_id"],
            "games",
        )

        base_columns = [
            "game_id",
            "game_date",
            "season",
            "home_team",
            "away_team",
            "home_sp_id",
            "away_sp_id",
        ]
        if "venue_id" in games.columns:
            base_columns.append("venue_id")
        if {"home_score", "away_score"}.issubset(games.columns):
            base_columns.extend(["home_score", "away_score"])

        features = games[base_columns].copy()
        features["prediction_mode"] = self.config.prediction_mode
        if {"home_score", "away_score"}.issubset(features.columns):
            features[TARGET_COLUMN] = (features["home_score"] > features["away_score"]).astype(int)

        starter_features = self._compute_starter_features(pitcher_logs)
        features = self._merge_home_away_player_features(
            features,
            starter_features,
            home_player_column="home_sp_id",
            away_player_column="away_sp_id",
            feature_prefix="sp_",
        )

        batter_profiles = self._compute_batter_pre_game_stats(batting_logs)
        lineup_features = self._compute_lineup_features(games, lineups, batter_profiles)
        features = self._merge_home_away_team_features(features, lineup_features, feature_prefix="lineup_")

        team_features = self._compute_team_features(games, batting_logs)
        features = self._merge_home_away_team_features(features, team_features, feature_prefix="team_")

        bullpen_features = self._compute_bullpen_features(games, pitcher_logs)
        features = self._merge_home_away_team_features(features, bullpen_features, feature_prefix="bullpen_")

        features = self._merge_park_weather_features(features, weather=weather, park_factors=park_factors)
        features = self._add_diff_features(features)
        features = features.sort_values(["game_date", "game_id"]).reset_index(drop=True)
        return features

    def _compute_batter_pre_game_stats(self, batting_logs: pd.DataFrame) -> pd.DataFrame:
        _require_columns(
            batting_logs,
            ["game_id", "game_date", "season", "player_id", "team"],
            "batting_logs",
        )
        out = _ensure_numeric_columns(batting_logs, BATTING_STATS)
        if "opposing_pitcher_hand" not in out.columns:
            out["opposing_pitcher_hand"] = np.nan
        out["opposing_pitcher_hand"] = out["opposing_pitcher_hand"].astype(str).str.upper().str[0]

        sort_columns = ["player_id", "season", "game_date", "game_id"]
        out = out.sort_values(sort_columns).reset_index(drop=True)
        group_keys = ["player_id", "season"]

        for column in BATTING_STATS:
            out[f"{column}_prior"] = out.groupby(group_keys, sort=False)[column].cumsum() - out[column]

        ops, woba, iso = _batting_rates_from_columns(out, suffix="_prior")
        out["batter_ops_season_to_date"] = ops
        out["batter_woba_season_to_date"] = woba
        out["batter_iso_season_to_date"] = iso
        statcast_columns = [column for column in BATTING_STATCAST_SUMS if column in out.columns]
        for column in statcast_columns:
            out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)
            out[f"{column}_prior"] = out.groupby(group_keys, sort=False)[column].cumsum() - out[column]
        if statcast_columns:
            out["batter_statcast_xwoba_to_date"] = _safe_divide(
                out.get("statcast_xwoba_sum_prior", 0.0),
                out.get("statcast_xwoba_count_prior", 0.0),
            )
            out["batter_statcast_woba_to_date"] = _safe_divide(
                out.get("statcast_woba_sum_prior", 0.0),
                out.get("statcast_woba_count_prior", 0.0),
            )
            out["batter_hard_hit_rate_to_date"] = _safe_divide(
                out.get("statcast_hard_hit_balls_prior", 0.0),
                out.get("statcast_batted_balls_prior", 0.0),
            )
            out["batter_barrel_rate_to_date"] = _safe_divide(
                out.get("statcast_barrels_prior", 0.0),
                out.get("statcast_batted_balls_prior", 0.0),
            )
            out["batter_avg_exit_velocity_to_date"] = _safe_divide(
                out.get("statcast_launch_speed_sum_prior", 0.0),
                out.get("statcast_batted_balls_prior", 0.0),
            )
        else:
            out["batter_statcast_xwoba_to_date"] = np.nan
            out["batter_statcast_woba_to_date"] = np.nan
            out["batter_hard_hit_rate_to_date"] = np.nan
            out["batter_barrel_rate_to_date"] = np.nan
            out["batter_avg_exit_velocity_to_date"] = np.nan

        for hand, label in [("R", "rhp"), ("L", "lhp")]:
            mask = out["opposing_pitcher_hand"] == hand
            for column in BATTING_STATS:
                contribution = out[column].where(mask, 0.0)
                out[f"{column}_prior_vs_{label}"] = contribution.groupby([out["player_id"], out["season"]], sort=False).cumsum() - contribution

            rate_frame = pd.DataFrame(
                {
                    f"{column}_prior": out[f"{column}_prior_vs_{label}"]
                    for column in BATTING_STATS
                }
            )
            _, hand_woba, _ = _batting_rates_from_columns(rate_frame, suffix="_prior")
            out[f"batter_woba_vs_{label}_to_date"] = hand_woba

        return out[
            [
                "game_id",
                "game_date",
                "season",
                "player_id",
                "batter_ops_season_to_date",
                "batter_woba_season_to_date",
                "batter_iso_season_to_date",
                "batter_woba_vs_rhp_to_date",
                "batter_woba_vs_lhp_to_date",
                "batter_statcast_xwoba_to_date",
                "batter_statcast_woba_to_date",
                "batter_hard_hit_rate_to_date",
                "batter_barrel_rate_to_date",
                "batter_avg_exit_velocity_to_date",
            ]
        ]

    def _compute_lineup_features(
        self,
        games: pd.DataFrame,
        lineups: pd.DataFrame,
        batter_profiles: pd.DataFrame,
    ) -> pd.DataFrame:
        _require_columns(lineups, ["game_id", "team", "player_id", "batting_order"], "lineups")
        out = lineups.copy()

        if "prediction_mode" in out.columns:
            aliases = {
                "confirmed_lineup": {"confirmed_lineup", "confirmed"},
                "pre_lineup": {"pre_lineup", "projected", "expected"},
            }[self.config.prediction_mode]
            filtered = out[out["prediction_mode"].astype(str).str.lower().isin(aliases)]
            if not filtered.empty:
                out = filtered

        if "game_date" not in out.columns or "season" not in out.columns:
            out = out.merge(games[["game_id", "game_date", "season"]], on="game_id", how="left")
        out = _with_datetime(out)
        out["batting_order"] = pd.to_numeric(out["batting_order"], errors="coerce")
        if "bats" not in out.columns:
            out["bats"] = np.nan
        out["bats"] = out["bats"].astype(str).str.upper().str[0]

        profile_columns = [
            "batter_ops_season_to_date",
            "batter_woba_season_to_date",
            "batter_iso_season_to_date",
            "batter_woba_vs_rhp_to_date",
            "batter_woba_vs_lhp_to_date",
            "batter_statcast_xwoba_to_date",
            "batter_statcast_woba_to_date",
            "batter_hard_hit_rate_to_date",
            "batter_barrel_rate_to_date",
            "batter_avg_exit_velocity_to_date",
        ]
        out = out.merge(
            batter_profiles[["game_id", "player_id", *profile_columns]],
            on=["game_id", "player_id"],
            how="left",
        )
        out = self._fill_missing_batter_profiles(out, batter_profiles, profile_columns)

        def aggregate(group: pd.DataFrame) -> pd.Series:
            weights = group["batting_order"].map(self.config.lineup_order_weights).fillna(0.10)
            weighted_woba = np.nan
            valid = group["batter_woba_season_to_date"].notna() & weights.notna()
            if valid.any() and float(weights.loc[valid].sum()) > 0:
                weighted_woba = float(np.average(group.loc[valid, "batter_woba_season_to_date"], weights=weights.loc[valid]))

            return pd.Series(
                {
                    "lineup_avg_ops": group["batter_ops_season_to_date"].mean(),
                    "lineup_avg_woba": group["batter_woba_season_to_date"].mean(),
                    "lineup_weighted_woba_by_order": weighted_woba,
                    "lineup_top3_woba": group.loc[group["batting_order"].between(1, 3), "batter_woba_season_to_date"].mean(),
                    "lineup_3to5_woba": group.loc[group["batting_order"].between(3, 5), "batter_woba_season_to_date"].mean(),
                    "lineup_bottom4_ops": group.loc[group["batting_order"] >= 6, "batter_ops_season_to_date"].mean(),
                    "lineup_lefty_ratio": group["bats"].isin(["L", "S"]).mean(),
                    "lineup_vs_rhp_woba": group["batter_woba_vs_rhp_to_date"].mean(),
                    "lineup_vs_lhp_woba": group["batter_woba_vs_lhp_to_date"].mean(),
                    "lineup_statcast_xwoba": group["batter_statcast_xwoba_to_date"].mean(),
                    "lineup_statcast_woba": group["batter_statcast_woba_to_date"].mean(),
                    "lineup_hard_hit_rate": group["batter_hard_hit_rate_to_date"].mean(),
                    "lineup_barrel_rate": group["batter_barrel_rate_to_date"].mean(),
                    "lineup_avg_exit_velocity": group["batter_avg_exit_velocity_to_date"].mean(),
                }
            )

        return out.groupby(["game_id", "team"], as_index=False).apply(aggregate, include_groups=False).reset_index(drop=True)

    def _fill_missing_batter_profiles(
        self,
        lineups: pd.DataFrame,
        batter_profiles: pd.DataFrame,
        profile_columns: list[str],
    ) -> pd.DataFrame:
        missing = lineups[profile_columns].isna().all(axis=1)
        if not missing.any():
            return lineups

        filled = lineups.copy()
        candidates = filled.loc[missing, ["player_id", "game_date"]].copy()
        candidates["_row_index"] = candidates.index
        history = batter_profiles[["player_id", "game_date", "game_id", *profile_columns]].copy()
        history = history.sort_values(["player_id", "game_date", "game_id"])

        pieces = []
        for player_id, player_candidates in candidates.groupby("player_id", sort=False):
            player_history = history[history["player_id"] == player_id]
            if player_history.empty:
                continue
            matched = pd.merge_asof(
                player_candidates.sort_values("game_date"),
                player_history.sort_values("game_date"),
                on="game_date",
                by="player_id",
                direction="backward",
                allow_exact_matches=False,
            )
            pieces.append(matched)

        if not pieces:
            return filled

        matches = pd.concat(pieces, ignore_index=True).set_index("_row_index")
        for column in profile_columns:
            if column in matches.columns:
                filled.loc[matches.index, column] = filled.loc[matches.index, column].fillna(matches[column])
        return filled

    def _compute_starter_features(self, pitcher_logs: pd.DataFrame) -> pd.DataFrame:
        _require_columns(
            pitcher_logs,
            ["game_id", "game_date", "season", "player_id", "team"],
            "pitcher_logs",
        )
        logs = _ensure_numeric_columns(pitcher_logs, PITCHING_STATS)
        if "is_start" in logs.columns:
            starts = logs[logs["is_start"].astype(float) == 1].copy()
        elif "role" in logs.columns:
            starts = logs[logs["role"].astype(str).str.upper().eq("SP")].copy()
        else:
            starts = logs.copy()

        starts = starts.sort_values(["player_id", "season", "game_date", "game_id"]).reset_index(drop=True)
        group_keys = ["player_id", "season"]
        for column in PITCHING_STATS:
            starts[f"{column}_prior"] = starts.groupby(group_keys, sort=False)[column].cumsum() - starts[column]

        starts["sp_fip_season_to_date"] = _pitching_fip(
            starts["innings_pitched_prior"],
            starts["home_runs_prior"],
            starts["walks_prior"],
            starts["hit_by_pitch_prior"],
            starts["strikeouts_prior"],
            self.config.fip_constant,
        )
        starts["sp_whip_season_to_date"] = _safe_divide(
            starts["hits_prior"] + starts["walks_prior"],
            starts["innings_pitched_prior"],
        )
        starts["sp_kbb_rate_season_to_date"] = _safe_divide(
            starts["strikeouts_prior"] - starts["walks_prior"],
            starts["batters_faced_prior"],
        )
        starts["start_fip"] = _pitching_fip(
            starts["innings_pitched"],
            starts["home_runs"],
            starts["walks"],
            starts["hit_by_pitch"],
            starts["strikeouts"],
            self.config.fip_constant,
        )

        grouped = starts.groupby(group_keys, group_keys=False, sort=False)
        starts["sp_fip_last_3_starts"] = grouped["start_fip"].apply(lambda series: series.shift(1).rolling(3, min_periods=1).mean())
        starts["sp_fip_last_5_starts"] = grouped["start_fip"].apply(lambda series: series.shift(1).rolling(5, min_periods=1).mean())
        starts["sp_ip_avg_last_3_starts"] = grouped["innings_pitched"].apply(lambda series: series.shift(1).rolling(3, min_periods=1).mean())
        starts["sp_pitch_count_last_start"] = grouped["pitches"].shift(1)
        starts["sp_rest_days"] = grouped["game_date"].diff().dt.days
        statcast_columns = [column for column in PITCHING_STATCAST_SUMS if column in starts.columns]
        for column in statcast_columns:
            starts[column] = pd.to_numeric(starts[column], errors="coerce").fillna(0.0)
            starts[f"{column}_prior"] = starts.groupby(group_keys, sort=False)[column].cumsum() - starts[column]
        if statcast_columns:
            starts["sp_statcast_xwoba_allowed_to_date"] = _safe_divide(
                starts.get("statcast_xwoba_allowed_sum_prior", 0.0),
                starts.get("statcast_xwoba_allowed_count_prior", 0.0),
            )
            starts["sp_statcast_woba_allowed_to_date"] = _safe_divide(
                starts.get("statcast_woba_allowed_sum_prior", 0.0),
                starts.get("statcast_woba_allowed_count_prior", 0.0),
            )
            starts["sp_hard_hit_rate_allowed_to_date"] = _safe_divide(
                starts.get("statcast_hard_hit_balls_allowed_prior", 0.0),
                starts.get("statcast_batted_balls_allowed_prior", 0.0),
            )
            starts["sp_barrel_rate_allowed_to_date"] = _safe_divide(
                starts.get("statcast_barrels_allowed_prior", 0.0),
                starts.get("statcast_batted_balls_allowed_prior", 0.0),
            )
            starts["sp_avg_exit_velocity_allowed_to_date"] = _safe_divide(
                starts.get("statcast_launch_speed_allowed_sum_prior", 0.0),
                starts.get("statcast_batted_balls_allowed_prior", 0.0),
            )
        else:
            starts["sp_statcast_xwoba_allowed_to_date"] = np.nan
            starts["sp_statcast_woba_allowed_to_date"] = np.nan
            starts["sp_hard_hit_rate_allowed_to_date"] = np.nan
            starts["sp_barrel_rate_allowed_to_date"] = np.nan
            starts["sp_avg_exit_velocity_allowed_to_date"] = np.nan

        return starts[
            [
                "game_id",
                "player_id",
                "sp_fip_season_to_date",
                "sp_whip_season_to_date",
                "sp_kbb_rate_season_to_date",
                "sp_fip_last_3_starts",
                "sp_fip_last_5_starts",
                "sp_ip_avg_last_3_starts",
                "sp_pitch_count_last_start",
                "sp_rest_days",
                "sp_statcast_xwoba_allowed_to_date",
                "sp_statcast_woba_allowed_to_date",
                "sp_hard_hit_rate_allowed_to_date",
                "sp_barrel_rate_allowed_to_date",
                "sp_avg_exit_velocity_allowed_to_date",
            ]
        ]

    def _compute_team_features(self, games: pd.DataFrame, batting_logs: pd.DataFrame) -> pd.DataFrame:
        team_rows = _team_game_rows(games)
        grouped = team_rows.groupby(["team", "season"], group_keys=False, sort=False)
        team_rows["team_games_played_to_date"] = grouped.cumcount()
        team_rows["team_runs_per_game_to_date"] = _safe_divide(
            grouped["runs_for"].cumsum().fillna(0) - team_rows["runs_for"].fillna(0),
            team_rows["team_games_played_to_date"],
        )
        team_rows["team_runs_allowed_per_game_to_date"] = _safe_divide(
            grouped["runs_allowed"].cumsum().fillna(0) - team_rows["runs_allowed"].fillna(0),
            team_rows["team_games_played_to_date"],
        )
        team_rows["team_recent_7g_win_rate"] = grouped["win"].apply(lambda series: series.shift(1).rolling(7, min_periods=1).mean())
        team_rows["team_recent_10g_win_rate"] = grouped["win"].apply(lambda series: series.shift(1).rolling(10, min_periods=1).mean())

        batting = _ensure_numeric_columns(batting_logs, BATTING_STATS)
        team_batting = (
            batting.groupby(["game_id", "team"], as_index=False)[BATTING_STATS]
            .sum()
        )
        team_rows = team_rows.merge(team_batting, on=["game_id", "team"], how="left")
        for column in BATTING_STATS:
            team_rows[column] = team_rows[column].fillna(0.0)
            team_rows[f"{column}_prior"] = team_rows.groupby(["team", "season"], sort=False)[column].cumsum() - team_rows[column]

        ops, woba, _ = _batting_rates_from_columns(team_rows, suffix="_prior")
        team_rows["team_ops_season_to_date"] = ops
        team_rows["team_woba_season_to_date"] = woba

        for days in [14, 30]:
            pieces = []
            for _, group in team_rows.groupby(["team", "season"], sort=False):
                group = group.sort_values(["game_date", "game_id"]).copy()
                rolling_sums: dict[str, pd.Series] = {}
                for column in BATTING_STATS:
                    rolling_sums[column] = _rolling_sum_before_dates(group, column, days)
                rolling_frame = pd.DataFrame(rolling_sums, index=group.index)
                ops_window, _, _ = _batting_rates_from_columns(rolling_frame)
                group[f"team_ops_last_{days}d"] = ops_window
                pieces.append(group[["game_id", "team", f"team_ops_last_{days}d"]])
            window = pd.concat(pieces, ignore_index=True)
            team_rows = team_rows.merge(window, on=["game_id", "team"], how="left")

        return team_rows[
            [
                "game_id",
                "team",
                "team_ops_season_to_date",
                "team_woba_season_to_date",
                "team_runs_per_game_to_date",
                "team_runs_allowed_per_game_to_date",
                "team_recent_7g_win_rate",
                "team_recent_10g_win_rate",
                "team_ops_last_14d",
                "team_ops_last_30d",
            ]
        ]

    def _compute_bullpen_features(self, games: pd.DataFrame, pitcher_logs: pd.DataFrame) -> pd.DataFrame:
        team_rows = _team_game_rows(games)[["game_id", "game_date", "season", "team"]]
        logs = _ensure_numeric_columns(pitcher_logs, PITCHING_STATS)
        if "is_start" in logs.columns:
            relief = logs[logs["is_start"].astype(float) == 0].copy()
        elif "role" in logs.columns:
            relief = logs[~logs["role"].astype(str).str.upper().eq("SP")].copy()
        else:
            relief = logs.iloc[0:0].copy()

        for optional_column in ["is_closer", "is_high_leverage"]:
            if optional_column not in relief.columns:
                relief[optional_column] = 0.0
            relief[optional_column] = pd.to_numeric(relief[optional_column], errors="coerce").fillna(0.0)

        relief["closer_ip"] = relief["innings_pitched"] * relief["is_closer"].clip(lower=0, upper=1)
        relief["high_leverage_ip"] = relief["innings_pitched"] * relief["is_high_leverage"].clip(lower=0, upper=1)
        aggregate_columns = [*PITCHING_STATS, "closer_ip", "high_leverage_ip"]
        relief_game = relief.groupby(["game_id", "team"], as_index=False)[aggregate_columns].sum()

        team_rows = team_rows.merge(relief_game, on=["game_id", "team"], how="left")
        for column in aggregate_columns:
            team_rows[column] = team_rows[column].fillna(0.0)
            team_rows[f"{column}_prior"] = team_rows.groupby(["team", "season"], sort=False)[column].cumsum() - team_rows[column]

        team_rows["bullpen_fip_season_to_date"] = _pitching_fip(
            team_rows["innings_pitched_prior"],
            team_rows["home_runs_prior"],
            team_rows["walks_prior"],
            team_rows["hit_by_pitch_prior"],
            team_rows["strikeouts_prior"],
            self.config.fip_constant,
        )
        team_rows["bullpen_whip_season_to_date"] = _safe_divide(
            team_rows["hits_prior"] + team_rows["walks_prior"],
            team_rows["innings_pitched_prior"],
        )

        pieces = []
        for _, group in team_rows.groupby(["team", "season"], sort=False):
            group = group.sort_values(["game_date", "game_id"]).copy()
            group["bullpen_ip_last_1d"] = _rolling_sum_before_dates(group, "innings_pitched", 1)
            group["bullpen_ip_last_3d"] = _rolling_sum_before_dates(group, "innings_pitched", 3)
            group["bullpen_ip_last_5d"] = _rolling_sum_before_dates(group, "innings_pitched", 5)
            group["high_leverage_rp_fatigue_score"] = _rolling_sum_before_dates(group, "high_leverage_ip", 3)
            yesterday_flags: list[float] = []
            dates = group["game_date"].reset_index(drop=True)
            closer_ip = group["closer_ip"].reset_index(drop=True)
            for current_date in dates:
                yesterday = current_date - pd.Timedelta(days=1)
                yesterday_flags.append(float(closer_ip.loc[dates == yesterday].sum() > 0))
            group["closer_used_yesterday"] = yesterday_flags
            pieces.append(group)
        team_rows = pd.concat(pieces, ignore_index=True)

        team_rows["bullpen_fatigue_score"] = (
            1.5 * team_rows["bullpen_ip_last_1d"]
            + 0.8 * team_rows["bullpen_ip_last_3d"]
            + 0.3 * team_rows["bullpen_ip_last_5d"]
            + 0.75 * team_rows["closer_used_yesterday"]
            + 0.5 * team_rows["high_leverage_rp_fatigue_score"]
        )

        return team_rows[
            [
                "game_id",
                "team",
                "bullpen_fip_season_to_date",
                "bullpen_whip_season_to_date",
                "bullpen_ip_last_1d",
                "bullpen_ip_last_3d",
                "bullpen_ip_last_5d",
                "closer_used_yesterday",
                "high_leverage_rp_fatigue_score",
                "bullpen_fatigue_score",
            ]
        ]

    def _merge_home_away_player_features(
        self,
        features: pd.DataFrame,
        source: pd.DataFrame,
        *,
        home_player_column: str,
        away_player_column: str,
        feature_prefix: str,
    ) -> pd.DataFrame:
        feature_columns = [column for column in source.columns if column.startswith(feature_prefix)]
        home_source = source[["game_id", "player_id", *feature_columns]].rename(
            columns={column: f"home_{column}" for column in feature_columns}
        )
        away_source = source[["game_id", "player_id", *feature_columns]].rename(
            columns={column: f"away_{column}" for column in feature_columns}
        )
        out = features.merge(
            home_source,
            left_on=["game_id", home_player_column],
            right_on=["game_id", "player_id"],
            how="left",
        ).drop(columns=["player_id"], errors="ignore")
        out = out.merge(
            away_source,
            left_on=["game_id", away_player_column],
            right_on=["game_id", "player_id"],
            how="left",
        ).drop(columns=["player_id"], errors="ignore")
        return out

    def _merge_home_away_team_features(
        self,
        features: pd.DataFrame,
        source: pd.DataFrame,
        *,
        feature_prefix: str,
    ) -> pd.DataFrame:
        feature_columns = [column for column in source.columns if column.startswith(feature_prefix)]
        if feature_prefix == "bullpen_":
            feature_columns.extend(
                [
                    column
                    for column in ["closer_used_yesterday", "high_leverage_rp_fatigue_score"]
                    if column in source.columns
                ]
            )
        home_source = source[["game_id", "team", *feature_columns]].rename(
            columns={column: f"home_{column}" for column in feature_columns}
        )
        away_source = source[["game_id", "team", *feature_columns]].rename(
            columns={column: f"away_{column}" for column in feature_columns}
        )
        out = features.merge(
            home_source,
            left_on=["game_id", "home_team"],
            right_on=["game_id", "team"],
            how="left",
        ).drop(columns=["team"], errors="ignore")
        out = out.merge(
            away_source,
            left_on=["game_id", "away_team"],
            right_on=["game_id", "team"],
            how="left",
        ).drop(columns=["team"], errors="ignore")
        return out

    def _merge_park_weather_features(
        self,
        features: pd.DataFrame,
        *,
        weather: pd.DataFrame | None,
        park_factors: pd.DataFrame | None,
    ) -> pd.DataFrame:
        out = features.copy()
        if weather is not None:
            _require_columns(weather, ["game_id"], "weather")
            weather_columns = [column for column in WEATHER_COLUMNS if column in weather.columns]
            out = out.merge(weather[["game_id", *weather_columns]], on="game_id", how="left")
        for column in WEATHER_COLUMNS:
            if column not in out.columns:
                out[column] = np.nan

        if park_factors is not None and "venue_id" in out.columns:
            _require_columns(park_factors, ["venue_id"], "park_factors")
            park_columns = [column for column in PARK_FACTOR_COLUMNS if column in park_factors.columns]
            if "season" in park_factors.columns:
                out = out.merge(park_factors[["venue_id", "season", *park_columns]], on=["venue_id", "season"], how="left")
            else:
                out = out.merge(park_factors[["venue_id", *park_columns]], on="venue_id", how="left")
        for column in PARK_FACTOR_COLUMNS:
            if column not in out.columns:
                out[column] = np.nan

        out["home_field_advantage"] = self.config.home_field_advantage
        return out

    def _add_diff_features(self, features: pd.DataFrame) -> pd.DataFrame:
        out = features.copy()
        out["sp_fip_diff"] = out["away_sp_fip_season_to_date"] - out["home_sp_fip_season_to_date"]
        out["lineup_woba_diff"] = out["home_lineup_avg_woba"] - out["away_lineup_avg_woba"]
        out["bullpen_fatigue_diff"] = out["away_bullpen_fatigue_score"] - out["home_bullpen_fatigue_score"]
        out["team_woba_diff"] = out["home_team_woba_season_to_date"] - out["away_team_woba_season_to_date"]
        out["lineup_statcast_xwoba_diff"] = out["home_lineup_statcast_xwoba"] - out["away_lineup_statcast_xwoba"]
        out["sp_statcast_xwoba_allowed_diff"] = (
            out["away_sp_statcast_xwoba_allowed_to_date"] - out["home_sp_statcast_xwoba_allowed_to_date"]
        )
        return out
