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
    "strikeouts",
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
    "earned_runs",
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
    "statcast_pitches",
    "statcast_whiffs",
    "statcast_batted_balls_allowed",
    "statcast_hard_hit_balls_allowed",
    "statcast_barrels_allowed",
    "statcast_xwoba_allowed_sum",
    "statcast_xwoba_allowed_count",
    "statcast_woba_allowed_sum",
    "statcast_woba_allowed_count",
    "statcast_launch_speed_allowed_sum",
    "statcast_release_speed_sum",
    "statcast_release_speed_count",
    "statcast_fastball_release_speed_sum",
    "statcast_fastball_release_speed_count",
    "statcast_spin_rate_sum",
    "statcast_spin_rate_count",
    "statcast_pitch_ff",
    "statcast_pitch_si",
    "statcast_pitch_fc",
    "statcast_pitch_sl",
    "statcast_pitch_cu",
    "statcast_pitch_ch",
    "statcast_pitch_fs",
]

WEATHER_COLUMNS = ["temperature", "wind_speed", "wind_direction", "humidity", "is_dome"]
PARK_FACTOR_COLUMNS = ["park_factor_run", "park_factor_hr"]
MARKET_LINE_COLUMNS = [
    "opening_total_line",
    "current_total_line",
    "closing_total_line",
    "over_odds",
    "under_odds",
    "opening_home_moneyline",
    "opening_away_moneyline",
    "current_home_moneyline",
    "current_away_moneyline",
    "home_sp_id_at_open",
    "away_sp_id_at_open",
    "home_sp_changed",
    "away_sp_changed",
    "starter_change_count",
]


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


def _american_implied_probability(values: pd.Series) -> pd.Series:
    odds = pd.to_numeric(values, errors="coerce")
    positive = odds > 0
    negative = odds < 0
    probability = pd.Series(np.nan, index=odds.index, dtype=float)
    probability.loc[positive] = 100.0 / (odds.loc[positive] + 100.0)
    probability.loc[negative] = odds.loc[negative].abs() / (odds.loc[negative].abs() + 100.0)
    return probability


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


def _batting_public_rates_from_columns(frame: pd.DataFrame, suffix: str = "") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    at_bats = frame[f"at_bats{suffix}"]
    hits = frame[f"hits{suffix}"]
    home_runs = frame[f"home_runs{suffix}"]
    walks = frame[f"walks{suffix}"]
    strikeouts = frame[f"strikeouts{suffix}"]
    sacrifice_flies = frame[f"sacrifice_flies{suffix}"]
    plate_appearances = frame[f"plate_appearances{suffix}"]
    balls_in_play = at_bats - strikeouts - home_runs + sacrifice_flies
    babip = _safe_divide(hits - home_runs, balls_in_play)
    bb_rate = _safe_divide(walks, plate_appearances)
    k_rate = _safe_divide(strikeouts, plate_appearances)
    return babip, bb_rate, k_rate


def _pitching_fip(
    innings: pd.Series,
    home_runs: pd.Series,
    walks: pd.Series,
    hit_by_pitch: pd.Series,
    strikeouts: pd.Series,
    fip_constant: float,
) -> np.ndarray:
    return _safe_divide(13 * home_runs + 3 * (walks + hit_by_pitch) - 2 * strikeouts, innings) + fip_constant


def _estimate_batters_faced(frame: pd.DataFrame) -> pd.Series:
    return (
        pd.to_numeric(frame["innings_pitched"], errors="coerce").fillna(0.0) * 3.0
        + pd.to_numeric(frame["hits"], errors="coerce").fillna(0.0)
        + pd.to_numeric(frame["walks"], errors="coerce").fillna(0.0)
        + pd.to_numeric(frame["hit_by_pitch"], errors="coerce").fillna(0.0)
    )


def _team_game_rows(games: pd.DataFrame) -> pd.DataFrame:
    _require_columns(
        games,
        ["game_id", "game_date", "season", "home_team", "away_team"],
        "games",
    )
    games = games.sort_values(["game_date", "game_id"]).drop_duplicates("game_id", keep="last").copy()
    optional_columns = [
        column
        for column in ["venue_id", "venue_latitude", "venue_longitude", "venue_timezone_offset"]
        if column in games.columns
    ]
    home = games[["game_id", "game_date", "season", "home_team", "away_team", *optional_columns]].copy()
    home = home.rename(columns={"home_team": "team", "away_team": "opponent"})
    home["is_home"] = 1
    away = games[["game_id", "game_date", "season", "away_team", "home_team", *optional_columns]].copy()
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


def _weighted_recent_before_current(
    values: pd.Series,
    *,
    window: int,
    decay: float = 0.85,
) -> pd.Series:
    raw = pd.to_numeric(values, errors="coerce").reset_index(drop=True)
    output: list[float] = []
    for index in range(len(raw)):
        prior = raw.iloc[max(0, index - window) : index].dropna().to_numpy(dtype=float)
        if len(prior) == 0:
            output.append(np.nan)
            continue
        weights = decay ** np.arange(len(prior) - 1, -1, -1, dtype=float)
        output.append(float(np.average(prior, weights=weights)))
    return pd.Series(output, index=values.index)


def _rolling_rate_before_current(values: pd.Series, *, window: int) -> pd.Series:
    values_series = pd.Series(values)
    raw = pd.to_numeric(values_series, errors="coerce").reset_index(drop=True)
    output: list[float] = []
    for index in range(len(raw)):
        prior = raw.iloc[max(0, index - window) : index].dropna()
        output.append(float(prior.mean()) if len(prior) else np.nan)
    return pd.Series(output, index=values_series.index)


def _haversine_miles(
    lat1: pd.Series,
    lon1: pd.Series,
    lat2: pd.Series,
    lon2: pd.Series,
) -> np.ndarray:
    lat1_arr = np.radians(pd.to_numeric(lat1, errors="coerce").to_numpy(dtype=float))
    lon1_arr = np.radians(pd.to_numeric(lon1, errors="coerce").to_numpy(dtype=float))
    lat2_arr = np.radians(pd.to_numeric(lat2, errors="coerce").to_numpy(dtype=float))
    lon2_arr = np.radians(pd.to_numeric(lon2, errors="coerce").to_numpy(dtype=float))
    dlat = lat2_arr - lat1_arr
    dlon = lon2_arr - lon1_arr
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1_arr) * np.cos(lat2_arr) * np.sin(dlon / 2) ** 2
    return 3958.7613 * 2 * np.arcsin(np.sqrt(a))


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
        venues: pd.DataFrame | None = None,
        market_lines: pd.DataFrame | None = None,
    ) -> pd.DataFrame:
        games = _with_datetime(games)
        games = self._merge_venue_metadata(games, venues)
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
        for optional_column in ["venue_latitude", "venue_longitude", "venue_timezone_offset"]:
            if optional_column in games.columns:
                base_columns.append(optional_column)
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
        matchup_context = self._lineup_matchup_context(games, batting_logs)
        lineup_features = self._compute_lineup_features(games, lineups, batter_profiles, matchup_context)
        features = self._merge_home_away_team_features(features, lineup_features, feature_prefix="lineup_")

        team_features = self._compute_team_features(games, batting_logs)
        features = self._merge_home_away_team_features(features, team_features, feature_prefix="team_")

        travel_features = self._compute_travel_features(games)
        features = self._merge_home_away_team_features(features, travel_features, feature_prefix="travel_")

        bullpen_features = self._compute_bullpen_features(games, pitcher_logs)
        features = self._merge_home_away_team_features(features, bullpen_features, feature_prefix="bullpen_")

        features = self._merge_park_weather_features(features, weather=weather, park_factors=park_factors)
        features = self._merge_market_line_features(features, market_lines=market_lines)
        features = self._add_diff_features(features)
        features = features.sort_values(["game_date", "game_id"]).reset_index(drop=True)
        return features

    def _merge_venue_metadata(self, games: pd.DataFrame, venues: pd.DataFrame | None) -> pd.DataFrame:
        out = games.copy()
        if venues is None or "venue_id" not in out.columns:
            return out
        _require_columns(venues, ["venue_id", "latitude", "longitude"], "venues")
        venue_columns = ["venue_id", "latitude", "longitude"]
        if "timezone_offset" in venues.columns:
            venue_columns.append("timezone_offset")
        venue_lookup = venues[venue_columns].copy()
        venue_lookup["venue_id"] = venue_lookup["venue_id"].astype("string")
        venue_lookup = venue_lookup.dropna(subset=["venue_id"]).drop_duplicates("venue_id", keep="last")
        venue_lookup = venue_lookup.rename(
            columns={
                "latitude": "venue_latitude",
                "longitude": "venue_longitude",
                "timezone_offset": "venue_timezone_offset",
            }
        )
        out["venue_id"] = out["venue_id"].astype("string")
        out = out.merge(venue_lookup, on="venue_id", how="left", suffixes=("", "_from_venues"))
        for column in ["venue_latitude", "venue_longitude", "venue_timezone_offset"]:
            fallback = f"{column}_from_venues"
            if fallback in out.columns:
                out[column] = out[column].fillna(out[fallback]) if column in out.columns else out[fallback]
                out = out.drop(columns=[fallback])
        if "venue_timezone_offset" not in out.columns:
            out["venue_timezone_offset"] = np.nan
        missing_timezone = out["venue_timezone_offset"].isna() & out.get("venue_longitude", pd.Series(index=out.index)).notna()
        out.loc[missing_timezone, "venue_timezone_offset"] = np.round(out.loc[missing_timezone, "venue_longitude"].astype(float) / 15.0)
        return out

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
        babip, bb_rate, k_rate = _batting_public_rates_from_columns(out, suffix="_prior")
        out["batter_ops_season_to_date"] = ops
        out["batter_woba_season_to_date"] = woba
        out["batter_iso_season_to_date"] = iso
        out["batter_babip_season_to_date"] = babip
        out["batter_bb_rate_season_to_date"] = bb_rate
        out["batter_k_rate_season_to_date"] = k_rate
        out["batter_xwoba_proxy"] = out["batter_woba_season_to_date"]
        out["batter_hard_contact_proxy"] = (
            out["batter_iso_season_to_date"].fillna(0.0)
            + 0.5 * out["batter_babip_season_to_date"].fillna(0.0)
        )
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
                "batter_babip_season_to_date",
                "batter_bb_rate_season_to_date",
                "batter_k_rate_season_to_date",
                "batter_xwoba_proxy",
                "batter_hard_contact_proxy",
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
        matchup_context: pd.DataFrame,
    ) -> pd.DataFrame:
        _require_columns(lineups, ["game_id", "team", "player_id", "batting_order"], "lineups")
        out = lineups.copy()

        if "prediction_mode" in out.columns:
            aliases = {
                "confirmed_lineup": {"confirmed_lineup", "confirmed"},
                "pre_lineup": {"pre_lineup", "projected", "expected"},
            }[self.config.prediction_mode]
            out = out[out["prediction_mode"].astype(str).str.lower().isin(aliases)].copy()
            if out.empty:
                return self._empty_lineup_features()

        missing_game_columns = [column for column in ["game_date", "season"] if column not in out.columns]
        if missing_game_columns:
            out = out.merge(games[["game_id", *missing_game_columns]], on="game_id", how="left")
        out = _with_datetime(out)
        out["batting_order"] = pd.to_numeric(out["batting_order"], errors="coerce")
        if pd.api.types.is_numeric_dtype(batter_profiles["player_id"]):
            out["player_id"] = pd.to_numeric(out["player_id"], errors="coerce")
        else:
            out["player_id"] = out["player_id"].astype(str)
        if "bats" not in out.columns:
            out["bats"] = np.nan
        out["bats"] = out["bats"].astype(str).str.upper().str[0]
        out = out.merge(matchup_context, on=["game_id", "team"], how="left")
        out = self._add_lineup_continuity(out)
        for optional_column in ["lineup_confidence", "is_available", "is_expected_starter", "rest_signal"]:
            if optional_column not in out.columns:
                out[optional_column] = np.nan
            out[optional_column] = pd.to_numeric(out[optional_column], errors="coerce")
        if self.config.prediction_mode == "confirmed_lineup":
            out["lineup_confidence"] = out["lineup_confidence"].fillna(1.0)
            out["is_available"] = out["is_available"].fillna(1.0)
            out["is_expected_starter"] = out["is_expected_starter"].fillna(1.0)
            out["rest_signal"] = out["rest_signal"].fillna(0.0)
        if "injury_status" not in out.columns:
            out["injury_status"] = np.nan
        injury_text = out["injury_status"].astype(str).str.lower()
        out["injury_absence_signal"] = injury_text.str.contains("il|injur|out|day-to-day|dtd|questionable", regex=True).astype(float)

        profile_columns = [
            "batter_ops_season_to_date",
            "batter_woba_season_to_date",
                "batter_iso_season_to_date",
                "batter_babip_season_to_date",
                "batter_bb_rate_season_to_date",
                "batter_k_rate_season_to_date",
                "batter_xwoba_proxy",
                "batter_hard_contact_proxy",
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
            opposing_hand = group["opposing_sp_hand"].dropna().iloc[0] if group["opposing_sp_hand"].notna().any() else np.nan
            if opposing_hand == "R":
                platoon_woba = group["batter_woba_vs_rhp_to_date"].mean()
                favorable = group["bats"].isin(["L", "S"])
                same_hand = group["bats"].eq("R")
            elif opposing_hand == "L":
                platoon_woba = group["batter_woba_vs_lhp_to_date"].mean()
                favorable = group["bats"].isin(["R", "S"])
                same_hand = group["bats"].eq("L")
            else:
                platoon_woba = np.nan
                favorable = pd.Series(False, index=group.index)
                same_hand = pd.Series(False, index=group.index)

            return pd.Series(
                {
                    "lineup_avg_ops": group["batter_ops_season_to_date"].mean(),
                    "lineup_avg_woba": group["batter_woba_season_to_date"].mean(),
                    "lineup_avg_iso": group["batter_iso_season_to_date"].mean(),
                    "lineup_avg_babip": group["batter_babip_season_to_date"].mean(),
                    "lineup_bb_rate": group["batter_bb_rate_season_to_date"].mean(),
                    "lineup_k_rate": group["batter_k_rate_season_to_date"].mean(),
                    "lineup_xwoba_proxy": group["batter_xwoba_proxy"].mean(),
                    "lineup_hard_contact_proxy": group["batter_hard_contact_proxy"].mean(),
                    "lineup_weighted_woba_by_order": weighted_woba,
                    "lineup_top3_woba": group.loc[group["batting_order"].between(1, 3), "batter_woba_season_to_date"].mean(),
                    "lineup_3to5_woba": group.loc[group["batting_order"].between(3, 5), "batter_woba_season_to_date"].mean(),
                    "lineup_bottom4_ops": group.loc[group["batting_order"] >= 6, "batter_ops_season_to_date"].mean(),
                    "lineup_lefty_ratio": group["bats"].isin(["L", "S"]).mean(),
                    "lineup_vs_rhp_woba": group["batter_woba_vs_rhp_to_date"].mean(),
                    "lineup_vs_lhp_woba": group["batter_woba_vs_lhp_to_date"].mean(),
                    "lineup_platoon_woba": platoon_woba,
                    "lineup_platoon_advantage_ratio": favorable.mean(),
                    "lineup_same_hand_ratio": same_hand.mean(),
                    "lineup_player_count": group["player_id"].nunique(),
                    "lineup_confidence": group["lineup_confidence"].mean(),
                    "lineup_available_ratio": group["is_available"].mean(),
                    "lineup_expected_starter_ratio": group["is_expected_starter"].mean(),
                    "lineup_rest_signal_count": group["rest_signal"].fillna(0.0).sum(),
                    "lineup_injury_absence_signal_count": group["injury_absence_signal"].fillna(0.0).sum(),
                    "lineup_previous_starter_return_rate": group["was_in_previous_lineup"].mean(),
                    "lineup_previous_starter_missing_count": group["previous_lineup_missing_count"].dropna().iloc[0]
                    if group["previous_lineup_missing_count"].notna().any()
                    else np.nan,
                    "lineup_statcast_xwoba": group["batter_statcast_xwoba_to_date"].mean(),
                    "lineup_statcast_woba": group["batter_statcast_woba_to_date"].mean(),
                    "lineup_hard_hit_rate": group["batter_hard_hit_rate_to_date"].mean(),
                    "lineup_barrel_rate": group["batter_barrel_rate_to_date"].mean(),
                    "lineup_avg_exit_velocity": group["batter_avg_exit_velocity_to_date"].mean(),
                }
            )

        return out.groupby(["game_id", "team"], as_index=False).apply(aggregate, include_groups=False).reset_index(drop=True)

    @staticmethod
    def _empty_lineup_features() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "game_id",
                "team",
                "lineup_avg_ops",
                "lineup_avg_woba",
                "lineup_avg_iso",
                "lineup_avg_babip",
                "lineup_bb_rate",
                "lineup_k_rate",
                "lineup_weighted_woba_by_order",
                "lineup_xwoba_proxy",
                "lineup_hard_contact_proxy",
                "lineup_top3_woba",
                "lineup_3to5_woba",
                "lineup_bottom4_ops",
                "lineup_lefty_ratio",
                "lineup_vs_rhp_woba",
                "lineup_vs_lhp_woba",
                "lineup_platoon_woba",
                "lineup_platoon_advantage_ratio",
                "lineup_same_hand_ratio",
                "lineup_player_count",
                "lineup_confidence",
                "lineup_available_ratio",
                "lineup_expected_starter_ratio",
                "lineup_rest_signal_count",
                "lineup_injury_absence_signal_count",
                "lineup_previous_starter_return_rate",
                "lineup_previous_starter_missing_count",
                "lineup_statcast_xwoba",
                "lineup_statcast_woba",
                "lineup_hard_hit_rate",
                "lineup_barrel_rate",
                "lineup_avg_exit_velocity",
            ]
        )

    def _add_lineup_continuity(self, lineups: pd.DataFrame) -> pd.DataFrame:
        out = lineups.sort_values(["team", "game_date", "game_id", "batting_order"]).copy()
        out["was_in_previous_lineup"] = np.nan
        out["previous_lineup_missing_count"] = np.nan
        for _, group in out.groupby("team", sort=False):
            previous_players: set[object] | None = None
            for game_id, game_group in group.groupby("game_id", sort=False):
                current_index = game_group.index
                current_players = set(game_group["player_id"].dropna().astype(str))
                if previous_players is not None and previous_players:
                    out.loc[current_index, "was_in_previous_lineup"] = game_group["player_id"].astype(str).isin(previous_players).astype(float)
                    out.loc[current_index, "previous_lineup_missing_count"] = float(len(previous_players - current_players))
                previous_players = current_players
        return out

    def _lineup_matchup_context(self, games: pd.DataFrame, batting_logs: pd.DataFrame) -> pd.DataFrame:
        game_team = _team_game_rows(games)[["game_id", "team"]].copy()
        if "opposing_pitcher_hand" in batting_logs.columns:
            logs = batting_logs[["game_id", "team", "opposing_pitcher_hand"]].copy()
            logs["opposing_sp_hand"] = logs["opposing_pitcher_hand"].astype(str).str.upper().str[0]
            logs = logs[logs["opposing_sp_hand"].isin(["R", "L"])]
            if not logs.empty:
                from_logs = (
                    logs.groupby(["game_id", "team"])["opposing_sp_hand"]
                    .agg(lambda values: values.mode().iloc[0] if not values.mode().empty else np.nan)
                    .reset_index()
                )
                game_team = game_team.merge(from_logs, on=["game_id", "team"], how="left")
            else:
                game_team["opposing_sp_hand"] = np.nan
        else:
            game_team["opposing_sp_hand"] = np.nan

        if {"home_sp_hand", "away_sp_hand"}.issubset(games.columns):
            hands = games[["game_id", "home_team", "away_team", "home_sp_hand", "away_sp_hand"]].copy()
            home = hands[["game_id", "home_team", "away_sp_hand"]].rename(
                columns={"home_team": "team", "away_sp_hand": "scheduled_opposing_sp_hand"}
            )
            away = hands[["game_id", "away_team", "home_sp_hand"]].rename(
                columns={"away_team": "team", "home_sp_hand": "scheduled_opposing_sp_hand"}
            )
            scheduled = pd.concat([home, away], ignore_index=True)
            scheduled["scheduled_opposing_sp_hand"] = scheduled["scheduled_opposing_sp_hand"].astype(str).str.upper().str[0]
            scheduled.loc[~scheduled["scheduled_opposing_sp_hand"].isin(["R", "L"]), "scheduled_opposing_sp_hand"] = np.nan
            game_team = game_team.merge(scheduled, on=["game_id", "team"], how="left")
            game_team["opposing_sp_hand"] = game_team["opposing_sp_hand"].fillna(game_team["scheduled_opposing_sp_hand"])
            game_team = game_team.drop(columns=["scheduled_opposing_sp_hand"])

        return game_team

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
        if pd.api.types.is_numeric_dtype(history["player_id"]):
            candidates["player_id"] = pd.to_numeric(candidates["player_id"], errors="coerce").astype(float)
            history["player_id"] = pd.to_numeric(history["player_id"], errors="coerce").astype(float)
            candidates = candidates.dropna(subset=["player_id"])
            history = history.dropna(subset=["player_id"])
        else:
            candidates["player_id"] = candidates["player_id"].astype(str)
            history["player_id"] = history["player_id"].astype(str)
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
        missing_bf = pd.to_numeric(logs["batters_faced"], errors="coerce").le(0)
        logs.loc[missing_bf, "batters_faced"] = _estimate_batters_faced(logs.loc[missing_bf])
        if "is_start" in logs.columns:
            starts = logs[logs["is_start"].astype(float) == 1].copy()
        elif "role" in logs.columns:
            starts = logs[logs["role"].astype(str).str.upper().eq("SP")].copy()
        else:
            starts = logs.copy()

        starts = starts.sort_values(["player_id", "season", "game_date", "game_id"]).reset_index(drop=True)
        group_keys = ["player_id", "season"]
        for column in PITCHING_STATS:
            # Fill before the cumulative sum so a synthetic scheduled-start row
            # (probable starter, no box score yet) carries the pitcher's prior
            # season-to-date instead of poisoning it to NaN. For played starts
            # the stat is present, so this is a no-op.
            filled = starts[column].fillna(0.0)
            starts[f"{column}_prior"] = filled.groupby([starts[key] for key in group_keys], sort=False).cumsum() - filled

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
        starts["sp_era_season_to_date"] = _safe_divide(
            9.0 * starts["earned_runs_prior"],
            starts["innings_pitched_prior"],
        )
        starts["sp_kbb_rate_season_to_date"] = _safe_divide(
            starts["strikeouts_prior"] - starts["walks_prior"],
            starts["batters_faced_prior"],
        )
        starts["sp_k_rate_season_to_date"] = _safe_divide(
            starts["strikeouts_prior"],
            starts["batters_faced_prior"],
        )
        starts["sp_bb_rate_season_to_date"] = _safe_divide(
            starts["walks_prior"],
            starts["batters_faced_prior"],
        )
        starts["sp_k_per_9_season_to_date"] = _safe_divide(
            9.0 * starts["strikeouts_prior"],
            starts["innings_pitched_prior"],
        )
        starts["sp_bb_per_9_season_to_date"] = _safe_divide(
            9.0 * starts["walks_prior"],
            starts["innings_pitched_prior"],
        )
        starts["sp_hr_per_9_season_to_date"] = _safe_divide(
            9.0 * starts["home_runs_prior"],
            starts["innings_pitched_prior"],
        )
        starts["sp_whiff_proxy"] = _safe_divide(
            starts["strikeouts_prior"],
            starts["batters_faced_prior"],
        )
        starts["sp_run_prevention_proxy"] = starts["sp_fip_season_to_date"]
        starts["sp_command_proxy"] = starts["sp_kbb_rate_season_to_date"]
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
            starts["sp_whiff_rate_to_date"] = _safe_divide(
                starts.get("statcast_whiffs_prior", 0.0),
                starts.get("statcast_pitches_prior", 0.0),
            )
            starts["sp_avg_fastball_velocity_to_date"] = _safe_divide(
                starts.get("statcast_fastball_release_speed_sum_prior", starts.get("statcast_release_speed_sum_prior", 0.0)),
                starts.get("statcast_fastball_release_speed_count_prior", starts.get("statcast_release_speed_count_prior", 0.0)),
            )
            starts["sp_avg_spin_rate_to_date"] = _safe_divide(
                starts.get("statcast_spin_rate_sum_prior", 0.0),
                starts.get("statcast_spin_rate_count_prior", 0.0),
            )
            starts["sp_fastball_usage_to_date"] = _safe_divide(
                starts.get("statcast_pitch_ff_prior", 0.0)
                + starts.get("statcast_pitch_si_prior", 0.0)
                + starts.get("statcast_pitch_fc_prior", 0.0),
                starts.get("statcast_pitches_prior", 0.0),
            )
            starts["sp_breaking_ball_usage_to_date"] = _safe_divide(
                starts.get("statcast_pitch_sl_prior", 0.0) + starts.get("statcast_pitch_cu_prior", 0.0),
                starts.get("statcast_pitches_prior", 0.0),
            )
            starts["sp_offspeed_usage_to_date"] = _safe_divide(
                starts.get("statcast_pitch_ch_prior", 0.0) + starts.get("statcast_pitch_fs_prior", 0.0),
                starts.get("statcast_pitches_prior", 0.0),
            )
        else:
            starts["sp_statcast_xwoba_allowed_to_date"] = np.nan
            starts["sp_statcast_woba_allowed_to_date"] = np.nan
            starts["sp_hard_hit_rate_allowed_to_date"] = np.nan
            starts["sp_barrel_rate_allowed_to_date"] = np.nan
            starts["sp_avg_exit_velocity_allowed_to_date"] = np.nan
            starts["sp_whiff_rate_to_date"] = np.nan
            starts["sp_avg_fastball_velocity_to_date"] = np.nan
            starts["sp_avg_spin_rate_to_date"] = np.nan
            starts["sp_fastball_usage_to_date"] = np.nan
            starts["sp_breaking_ball_usage_to_date"] = np.nan
            starts["sp_offspeed_usage_to_date"] = np.nan

        return starts[
            [
                "game_id",
                "player_id",
                "sp_fip_season_to_date",
                "sp_whip_season_to_date",
                "sp_era_season_to_date",
                "sp_kbb_rate_season_to_date",
                "sp_k_rate_season_to_date",
                "sp_bb_rate_season_to_date",
                "sp_k_per_9_season_to_date",
                "sp_bb_per_9_season_to_date",
                "sp_hr_per_9_season_to_date",
                "sp_whiff_proxy",
                "sp_run_prevention_proxy",
                "sp_command_proxy",
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
                "sp_whiff_rate_to_date",
                "sp_avg_fastball_velocity_to_date",
                "sp_avg_spin_rate_to_date",
                "sp_fastball_usage_to_date",
                "sp_breaking_ball_usage_to_date",
                "sp_offspeed_usage_to_date",
            ]
        ]

    def _compute_team_features(self, games: pd.DataFrame, batting_logs: pd.DataFrame) -> pd.DataFrame:
        team_rows = _team_game_rows(games)
        team_rows = _with_datetime(team_rows)
        # Fill scores before the cumulative sum so a scheduled (not-yet-played)
        # game with NaN runs does not poison its own running total to NaN/0; the
        # prior-game average still carries forward. No-op for played games.
        team_rows["_runs_for_filled"] = team_rows["runs_for"].fillna(0)
        team_rows["_runs_allowed_filled"] = team_rows["runs_allowed"].fillna(0)
        grouped = team_rows.groupby(["team", "season"], group_keys=False, sort=False)
        team_rows["team_games_played_to_date"] = grouped.cumcount()
        team_rows["team_runs_per_game_to_date"] = _safe_divide(
            grouped["_runs_for_filled"].cumsum() - team_rows["_runs_for_filled"],
            team_rows["team_games_played_to_date"],
        )
        team_rows["team_runs_allowed_per_game_to_date"] = _safe_divide(
            grouped["_runs_allowed_filled"].cumsum() - team_rows["_runs_allowed_filled"],
            team_rows["team_games_played_to_date"],
        )
        team_rows["team_recent_7g_win_rate"] = grouped["win"].apply(lambda series: series.shift(1).rolling(7, min_periods=1).mean())
        team_rows["team_recent_10g_win_rate"] = grouped["win"].apply(lambda series: series.shift(1).rolling(10, min_periods=1).mean())
        team_rows["run_diff"] = team_rows["runs_for"] - team_rows["runs_allowed"]
        team_rows["one_run_game"] = team_rows["run_diff"].abs().eq(1).astype(float)
        team_rows["one_run_win"] = np.where(team_rows["one_run_game"].eq(1), team_rows["win"], np.nan)

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
        _, team_bb_rate, team_k_rate = _batting_public_rates_from_columns(team_rows, suffix="_prior")
        team_rows["team_ops_season_to_date"] = ops
        team_rows["team_woba_season_to_date"] = woba
        team_rows["team_bb_rate_season_to_date"] = team_bb_rate
        team_rows["team_k_rate_season_to_date"] = team_k_rate

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

        recent_pieces = []
        for _, group in team_rows.groupby(["team", "season"], sort=False):
            group = group.sort_values(["game_date", "game_id"]).copy()
            group["team_weighted_win_rate_last_10"] = _weighted_recent_before_current(group["win"], window=10)
            group["team_weighted_win_rate_last_20"] = _weighted_recent_before_current(group["win"], window=20)
            group["team_weighted_run_diff_last_10"] = _weighted_recent_before_current(group["run_diff"], window=10)
            group["team_weighted_run_diff_last_20"] = _weighted_recent_before_current(group["run_diff"], window=20)
            group["team_weighted_runs_for_last_10"] = _weighted_recent_before_current(group["runs_for"], window=10)
            group["team_weighted_runs_allowed_last_10"] = _weighted_recent_before_current(group["runs_allowed"], window=10)
            group["team_low_run_rate_last_10"] = _rolling_rate_before_current(group["runs_for"].le(2).astype(float), window=10)
            group["team_5plus_run_rate_last_10"] = _rolling_rate_before_current(group["runs_for"].ge(5).astype(float), window=10)
            group["team_one_run_game_rate_last_20"] = _rolling_rate_before_current(group["one_run_game"], window=20)
            group["team_one_run_win_rate_last_20"] = _rolling_rate_before_current(group["one_run_win"], window=20)
            group["team_runs_for_volatility_last_10"] = group["runs_for"].shift(1).rolling(10, min_periods=2).std()
            wins_20 = group["win"].shift(1).rolling(20, min_periods=1).mean()
            runs_for_20 = group["runs_for"].shift(1).rolling(20, min_periods=1).sum()
            runs_allowed_20 = group["runs_allowed"].shift(1).rolling(20, min_periods=1).sum()
            pythag_denominator = runs_for_20.pow(2) + runs_allowed_20.pow(2)
            group["team_pythagorean_win_pct_last_20"] = np.divide(
                runs_for_20.pow(2),
                pythag_denominator,
                out=np.full(len(group), np.nan, dtype=float),
                where=pythag_denominator.to_numpy(dtype=float) > 0,
            )
            group["team_actual_minus_pythag_last_20"] = wins_20 - group["team_pythagorean_win_pct_last_20"]
            group["team_close_win_dependency_last_20"] = _rolling_rate_before_current(
                pd.Series(np.where(group["win"].eq(1), group["one_run_game"], np.nan), index=group.index),
                window=20,
            )
            recent_pieces.append(
                group[
                    [
                        "game_id",
                        "team",
                        "team_weighted_win_rate_last_10",
                        "team_weighted_win_rate_last_20",
                        "team_weighted_run_diff_last_10",
                        "team_weighted_run_diff_last_20",
                        "team_weighted_runs_for_last_10",
                        "team_weighted_runs_allowed_last_10",
                        "team_low_run_rate_last_10",
                        "team_5plus_run_rate_last_10",
                        "team_one_run_game_rate_last_20",
                        "team_one_run_win_rate_last_20",
                        "team_runs_for_volatility_last_10",
                        "team_pythagorean_win_pct_last_20",
                        "team_actual_minus_pythag_last_20",
                        "team_close_win_dependency_last_20",
                    ]
                ]
            )
        recent = pd.concat(recent_pieces, ignore_index=True)
        team_rows = team_rows.merge(recent, on=["game_id", "team"], how="left")

        return team_rows[
            [
                "game_id",
                "team",
                "team_ops_season_to_date",
                "team_woba_season_to_date",
                "team_bb_rate_season_to_date",
                "team_k_rate_season_to_date",
                "team_runs_per_game_to_date",
                "team_runs_allowed_per_game_to_date",
                "team_recent_7g_win_rate",
                "team_recent_10g_win_rate",
                "team_ops_last_14d",
                "team_ops_last_30d",
                "team_weighted_win_rate_last_10",
                "team_weighted_win_rate_last_20",
                "team_weighted_run_diff_last_10",
                "team_weighted_run_diff_last_20",
                "team_weighted_runs_for_last_10",
                "team_weighted_runs_allowed_last_10",
                "team_low_run_rate_last_10",
                "team_5plus_run_rate_last_10",
                "team_one_run_game_rate_last_20",
                "team_one_run_win_rate_last_20",
                "team_runs_for_volatility_last_10",
                "team_pythagorean_win_pct_last_20",
                "team_actual_minus_pythag_last_20",
                "team_close_win_dependency_last_20",
            ]
        ]

    def _compute_travel_features(self, games: pd.DataFrame) -> pd.DataFrame:
        team_rows = _team_game_rows(games)
        for column in ["venue_latitude", "venue_longitude", "venue_timezone_offset"]:
            if column not in team_rows.columns:
                team_rows[column] = np.nan
            team_rows[column] = pd.to_numeric(team_rows[column], errors="coerce")

        pieces = []
        for _, group in team_rows.groupby(["team", "season"], sort=False):
            group = group.sort_values(["game_date", "game_id"]).copy()
            previous_date = group["game_date"].shift(1)
            group["travel_rest_days"] = (group["game_date"] - previous_date).dt.days
            group["travel_distance_miles"] = _haversine_miles(
                group["venue_latitude"].shift(1),
                group["venue_longitude"].shift(1),
                group["venue_latitude"],
                group["venue_longitude"],
            )
            group.loc[group["travel_rest_days"].isna(), "travel_distance_miles"] = np.nan
            group["travel_timezone_shift"] = group["venue_timezone_offset"] - group["venue_timezone_offset"].shift(1)
            group["travel_is_back_to_back"] = group["travel_rest_days"].eq(1).astype(float)
            group["travel_travel_day"] = (
                group["travel_rest_days"].le(1) & group["travel_distance_miles"].fillna(0).gt(100)
            ).astype(float)
            group["travel_away_game_streak"] = group["is_home"].eq(0).groupby(group["is_home"].ne(group["is_home"].shift()).cumsum()).cumcount() + 1
            group.loc[group["is_home"].eq(1), "travel_away_game_streak"] = 0
            group["travel_home_game_streak"] = group["is_home"].eq(1).groupby(group["is_home"].ne(group["is_home"].shift()).cumsum()).cumcount() + 1
            group.loc[group["is_home"].eq(0), "travel_home_game_streak"] = 0
            pieces.append(group)

        out = pd.concat(pieces, ignore_index=True) if pieces else team_rows
        return out[
            [
                "game_id",
                "team",
                "travel_rest_days",
                "travel_distance_miles",
                "travel_timezone_shift",
                "travel_is_back_to_back",
                "travel_travel_day",
                "travel_away_game_streak",
                "travel_home_game_streak",
            ]
        ]

    def _compute_bullpen_features(self, games: pd.DataFrame, pitcher_logs: pd.DataFrame) -> pd.DataFrame:
        team_rows = _team_game_rows(games)[["game_id", "game_date", "season", "team"]]
        logs = _ensure_numeric_columns(pitcher_logs, PITCHING_STATS)
        missing_bf = pd.to_numeric(logs["batters_faced"], errors="coerce").le(0)
        logs.loc[missing_bf, "batters_faced"] = _estimate_batters_faced(logs.loc[missing_bf])
        if "is_start" in logs.columns:
            relief = logs[logs["is_start"].astype(float) == 0].copy()
        elif "role" in logs.columns:
            relief = logs[~logs["role"].astype(str).str.upper().eq("SP")].copy()
        else:
            relief = logs.iloc[0:0].copy()

        role_signal_columns = ["saves", "holds", "games_finished", "save_opportunities", "blown_saves"]
        for optional_column in ["is_closer", "is_high_leverage", *role_signal_columns]:
            if optional_column not in relief.columns:
                relief[optional_column] = 0.0
            relief[optional_column] = pd.to_numeric(relief[optional_column], errors="coerce").fillna(0.0)

        relief = relief.sort_values(["player_id", "season", "game_date", "game_id"]).copy()
        relief["relief_appearances"] = 1.0
        group_keys = ["player_id", "season"]
        for column in [*role_signal_columns, "relief_appearances"]:
            relief[f"{column}_prior"] = relief.groupby(group_keys, sort=False)[column].cumsum() - relief[column]
        relief["estimated_high_leverage_role_score"] = _safe_divide(
            3.0 * relief["saves_prior"]
            + 2.0 * relief["holds_prior"]
            + relief["games_finished_prior"]
            + 2.0 * relief["save_opportunities_prior"]
            + relief["blown_saves_prior"],
            relief["relief_appearances_prior"],
        )
        relief["estimated_high_leverage_role_score"] = relief["estimated_high_leverage_role_score"].fillna(
            relief["is_high_leverage"].clip(lower=0, upper=1)
        )
        relief["closer_ip"] = relief["innings_pitched"] * relief["is_closer"].clip(lower=0, upper=1)
        relief["high_leverage_ip"] = relief["innings_pitched"] * relief["is_high_leverage"].clip(lower=0, upper=1)
        relief["estimated_high_leverage_role_ip"] = relief["innings_pitched"] * relief[
            "estimated_high_leverage_role_score"
        ].clip(lower=0, upper=1)
        aggregate_columns = [*PITCHING_STATS, "closer_ip", "high_leverage_ip", "estimated_high_leverage_role_ip"]
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
            group["estimated_high_leverage_role_fatigue_score"] = _rolling_sum_before_dates(group, "estimated_high_leverage_role_ip", 3)
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
            + 0.25 * team_rows["estimated_high_leverage_role_fatigue_score"]
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
                "estimated_high_leverage_role_fatigue_score",
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
                    for column in [
                        "closer_used_yesterday",
                        "high_leverage_rp_fatigue_score",
                        "estimated_high_leverage_role_fatigue_score",
                    ]
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
            out["venue_id"] = out["venue_id"].astype("string")
            park_factors = park_factors.copy()
            park_factors["venue_id"] = park_factors["venue_id"].astype("string")
            if "season" in park_factors.columns:
                out = out.merge(park_factors[["venue_id", "season", *park_columns]], on=["venue_id", "season"], how="left")
            else:
                out = out.merge(park_factors[["venue_id", *park_columns]], on="venue_id", how="left")
        for column in PARK_FACTOR_COLUMNS:
            if column not in out.columns:
                out[column] = np.nan

        out["home_field_advantage"] = self.config.home_field_advantage
        return out

    def _merge_market_line_features(
        self,
        features: pd.DataFrame,
        *,
        market_lines: pd.DataFrame | None,
    ) -> pd.DataFrame:
        out = features.copy()
        if market_lines is None:
            for column in [
                "market_opening_total_line",
                "market_current_total_line",
                "market_total_line",
                "market_closing_total_line",
                "market_total_line_movement",
                "market_over_odds",
                "market_under_odds",
                "market_over_implied_prob",
                "market_under_implied_prob",
                "market_ou_vig",
                "market_opening_home_moneyline",
                "market_opening_away_moneyline",
                "market_current_home_moneyline",
                "market_current_away_moneyline",
                "market_home_moneyline_movement",
                "market_away_moneyline_movement",
                "market_home_sp_changed",
                "market_away_sp_changed",
                "market_starter_change_count",
            ]:
                out[column] = np.nan
            return out

        _require_columns(market_lines, ["game_id"], "market_lines")
        lines = market_lines.copy()
        lines["game_id"] = lines["game_id"].astype(str)
        out["game_id"] = out["game_id"].astype(str)
        for column in MARKET_LINE_COLUMNS:
            if column not in lines.columns:
                lines[column] = np.nan
        numeric_columns = [
            "opening_total_line",
            "current_total_line",
            "closing_total_line",
            "over_odds",
            "under_odds",
            "opening_home_moneyline",
            "opening_away_moneyline",
            "current_home_moneyline",
            "current_away_moneyline",
            "home_sp_changed",
            "away_sp_changed",
            "starter_change_count",
        ]
        for column in numeric_columns:
            lines[column] = pd.to_numeric(lines[column], errors="coerce")

        lines = lines.drop_duplicates("game_id", keep="last")
        lines["market_opening_total_line"] = lines["opening_total_line"]
        lines["market_current_total_line"] = lines["current_total_line"]
        lines["market_total_line"] = lines["current_total_line"].fillna(lines["opening_total_line"])
        lines["market_closing_total_line"] = lines["closing_total_line"]
        lines["market_total_line_movement"] = lines["current_total_line"] - lines["opening_total_line"]
        lines["market_over_odds"] = lines["over_odds"]
        lines["market_under_odds"] = lines["under_odds"]
        lines["market_over_implied_prob"] = _american_implied_probability(lines["over_odds"])
        lines["market_under_implied_prob"] = _american_implied_probability(lines["under_odds"])
        lines["market_ou_vig"] = lines["market_over_implied_prob"] + lines["market_under_implied_prob"] - 1.0
        lines["market_opening_home_moneyline"] = lines["opening_home_moneyline"]
        lines["market_opening_away_moneyline"] = lines["opening_away_moneyline"]
        lines["market_current_home_moneyline"] = lines["current_home_moneyline"]
        lines["market_current_away_moneyline"] = lines["current_away_moneyline"]
        lines["market_home_moneyline_movement"] = lines["current_home_moneyline"] - lines["opening_home_moneyline"]
        lines["market_away_moneyline_movement"] = lines["current_away_moneyline"] - lines["opening_away_moneyline"]

        home_changed = lines["home_sp_changed"]
        away_changed = lines["away_sp_changed"]
        if "home_sp_id_at_open" in lines.columns:
            current_home_sp = out.set_index("game_id").reindex(lines["game_id"])["home_sp_id"].reset_index(drop=True)
            home_open = lines["home_sp_id_at_open"].reset_index(drop=True)
            inferred_home_changed = home_open.notna() & current_home_sp.astype(str).ne(home_open.astype(str))
            inferred_home_changed.index = lines.index
            home_changed = home_changed.fillna(inferred_home_changed.astype(float))
        if "away_sp_id_at_open" in lines.columns:
            current_away_sp = out.set_index("game_id").reindex(lines["game_id"])["away_sp_id"].reset_index(drop=True)
            away_open = lines["away_sp_id_at_open"].reset_index(drop=True)
            inferred_away_changed = away_open.notna() & current_away_sp.astype(str).ne(away_open.astype(str))
            inferred_away_changed.index = lines.index
            away_changed = away_changed.fillna(inferred_away_changed.astype(float))
        lines["market_home_sp_changed"] = pd.to_numeric(home_changed, errors="coerce")
        lines["market_away_sp_changed"] = pd.to_numeric(away_changed, errors="coerce")
        lines["market_starter_change_count"] = lines["starter_change_count"].fillna(
            lines["market_home_sp_changed"].fillna(0.0) + lines["market_away_sp_changed"].fillna(0.0)
        )

        market_columns = [column for column in lines.columns if column.startswith("market_")]
        return out.merge(lines[["game_id", *market_columns]], on="game_id", how="left")

    def _add_diff_features(self, features: pd.DataFrame) -> pd.DataFrame:
        out = features.copy()
        out["sp_fip_diff"] = out["away_sp_fip_season_to_date"] - out["home_sp_fip_season_to_date"]
        out["lineup_woba_diff"] = out["home_lineup_avg_woba"] - out["away_lineup_avg_woba"]
        out["lineup_iso_diff"] = out["home_lineup_avg_iso"] - out["away_lineup_avg_iso"]
        out["lineup_bb_rate_diff"] = out["home_lineup_bb_rate"] - out["away_lineup_bb_rate"]
        out["lineup_k_rate_diff"] = out["away_lineup_k_rate"] - out["home_lineup_k_rate"]
        out["lineup_platoon_woba_diff"] = out["home_lineup_platoon_woba"] - out["away_lineup_platoon_woba"]
        out["lineup_platoon_advantage_diff"] = (
            out["home_lineup_platoon_advantage_ratio"] - out["away_lineup_platoon_advantage_ratio"]
        )
        out["bullpen_fatigue_diff"] = out["away_bullpen_fatigue_score"] - out["home_bullpen_fatigue_score"]
        out["team_woba_diff"] = out["home_team_woba_season_to_date"] - out["away_team_woba_season_to_date"]
        out["team_bb_rate_diff"] = out["home_team_bb_rate_season_to_date"] - out["away_team_bb_rate_season_to_date"]
        out["team_k_rate_diff"] = out["away_team_k_rate_season_to_date"] - out["home_team_k_rate_season_to_date"]
        out["team_weighted_win_rate_last_10_diff"] = (
            out["home_team_weighted_win_rate_last_10"] - out["away_team_weighted_win_rate_last_10"]
        )
        out["team_weighted_run_diff_last_10_diff"] = (
            out["home_team_weighted_run_diff_last_10"] - out["away_team_weighted_run_diff_last_10"]
        )
        out["team_weighted_runs_for_last_10_diff"] = (
            out["home_team_weighted_runs_for_last_10"] - out["away_team_weighted_runs_for_last_10"]
        )
        out["team_weighted_runs_allowed_last_10_diff"] = (
            out["away_team_weighted_runs_allowed_last_10"] - out["home_team_weighted_runs_allowed_last_10"]
        )
        out["team_low_run_rate_last_10_diff"] = (
            out["away_team_low_run_rate_last_10"] - out["home_team_low_run_rate_last_10"]
        )
        out["team_5plus_run_rate_last_10_diff"] = (
            out["home_team_5plus_run_rate_last_10"] - out["away_team_5plus_run_rate_last_10"]
        )
        out["team_actual_minus_pythag_last_20_diff"] = (
            out["home_team_actual_minus_pythag_last_20"] - out["away_team_actual_minus_pythag_last_20"]
        )
        out["team_close_win_dependency_last_20_diff"] = (
            out["home_team_close_win_dependency_last_20"] - out["away_team_close_win_dependency_last_20"]
        )
        out["lineup_statcast_xwoba_diff"] = out["home_lineup_statcast_xwoba"] - out["away_lineup_statcast_xwoba"]
        out["lineup_xwoba_proxy_diff"] = out["home_lineup_xwoba_proxy"] - out["away_lineup_xwoba_proxy"]
        out["lineup_hard_contact_proxy_diff"] = (
            out["home_lineup_hard_contact_proxy"] - out["away_lineup_hard_contact_proxy"]
        )
        out["sp_statcast_xwoba_allowed_diff"] = (
            out["away_sp_statcast_xwoba_allowed_to_date"] - out["home_sp_statcast_xwoba_allowed_to_date"]
        )
        out["lineup_confidence_diff"] = out["home_lineup_confidence"] - out["away_lineup_confidence"]
        out["lineup_previous_starter_return_diff"] = (
            out["home_lineup_previous_starter_return_rate"] - out["away_lineup_previous_starter_return_rate"]
        )
        out["lineup_injury_absence_signal_diff"] = (
            out["away_lineup_injury_absence_signal_count"] - out["home_lineup_injury_absence_signal_count"]
        )
        out["travel_distance_diff"] = out["away_travel_distance_miles"] - out["home_travel_distance_miles"]
        out["travel_rest_diff"] = out["home_travel_rest_days"] - out["away_travel_rest_days"]
        out["travel_timezone_shift_diff"] = out["away_travel_timezone_shift"].abs() - out["home_travel_timezone_shift"].abs()
        out["sp_whiff_rate_diff"] = out["home_sp_whiff_rate_to_date"] - out["away_sp_whiff_rate_to_date"]
        out["sp_whiff_proxy_diff"] = out["home_sp_whiff_proxy"] - out["away_sp_whiff_proxy"]
        out["sp_run_prevention_proxy_diff"] = out["away_sp_run_prevention_proxy"] - out["home_sp_run_prevention_proxy"]
        out["sp_command_proxy_diff"] = out["home_sp_command_proxy"] - out["away_sp_command_proxy"]
        out["sp_era_diff"] = out["away_sp_era_season_to_date"] - out["home_sp_era_season_to_date"]
        out["sp_k_rate_public_diff"] = out["home_sp_k_rate_season_to_date"] - out["away_sp_k_rate_season_to_date"]
        out["sp_bb_rate_public_diff"] = out["away_sp_bb_rate_season_to_date"] - out["home_sp_bb_rate_season_to_date"]
        out["sp_fastball_velocity_diff"] = out["home_sp_avg_fastball_velocity_to_date"] - out["away_sp_avg_fastball_velocity_to_date"]
        return out
