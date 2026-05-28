"""Historical market odds (totals/ML/spread) standardization and game matching.

Source: ArnavSaraogi/mlb-odds-scraper SBR-derived JSON dump (2021-03-20 .. 2025-08-16).
Schema per game: gameView {startDate, awayTeam, homeTeam, scores, venueName, gameType}
                 odds {moneyline[], pointspread[], totals[]}, each with sportsbook and
                 openingLine + currentLine. currentLine ~ closing line near game time.
"""

from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

# SBR shortName -> our standardized team abbreviation in data/standardized/mlb_stats_api_*/games.csv
SBR_TEAM_MAP: dict[str, str] = {
    "ARI": "AZ",
    "AZ": "AZ",
    "CHW": "CWS",
    "WAS": "WSH",
    # ATH (Athletics 2025+ rebrand) and OAK both appear as-is; the
    # match-by-date logic will pick whichever exists in that season's games.csv.
}

STANDARD_ODDS_COLUMNS = [
    "game_date",
    "away_team",
    "home_team",
    "away_score",
    "home_score",
    "venue_name",
    "n_books_total",
    "total_open_median",
    "total_close_median",
    "over_odds_close_median",
    "under_odds_close_median",
    "ml_home_open_median",
    "ml_away_open_median",
    "ml_home_close_median",
    "ml_away_close_median",
    "spread_home_close_median",
    "spread_home_close_odds_median",
    "spread_away_close_odds_median",
    "source",
]


def _safe_median(values: Iterable[float | int | None]) -> float | None:
    vals = [float(v) for v in values if v is not None and not (isinstance(v, float) and np.isnan(v))]
    if not vals:
        return None
    return float(statistics.median(vals))


def _normalize_team(short: str) -> str:
    return SBR_TEAM_MAP.get(short, short)


def parse_sbr_odds_dataset(json_path: str | Path) -> pd.DataFrame:
    """Parse the SBR-derived JSON odds dataset into a flat one-row-per-game DataFrame.

    Aggregates across sportsbooks using the median (robust to outlier off-market books).
    Filters out non-MLB-game rows (AL/NL All-Star, gameType not 'R'/'P'/'F'/etc.).
    """

    with Path(json_path).open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    rows: list[dict[str, object]] = []
    for date_str, games in raw.items():
        if not isinstance(games, list):
            continue
        for game in games:
            view = game.get("gameView") or {}
            odds = game.get("odds") or {}
            away = view.get("awayTeam") or {}
            home = view.get("homeTeam") or {}
            away_short = (away.get("shortName") or "").strip().upper()
            home_short = (home.get("shortName") or "").strip().upper()
            if away_short in {"AL", "NL"} or home_short in {"AL", "NL"}:
                continue  # All-Star game
            if not away_short or not home_short:
                continue

            totals = odds.get("totals") or []
            ml = odds.get("moneyline") or []
            spread = odds.get("pointspread") or []

            total_open = [t.get("openingLine", {}).get("total") for t in totals]
            total_close = [t.get("currentLine", {}).get("total") for t in totals]
            over_close = [t.get("currentLine", {}).get("overOdds") for t in totals]
            under_close = [t.get("currentLine", {}).get("underOdds") for t in totals]

            ml_home_open = [m.get("openingLine", {}).get("homeOdds") for m in ml]
            ml_away_open = [m.get("openingLine", {}).get("awayOdds") for m in ml]
            ml_home_close = [m.get("currentLine", {}).get("homeOdds") for m in ml]
            ml_away_close = [m.get("currentLine", {}).get("awayOdds") for m in ml]

            sp_home_close = [s.get("currentLine", {}).get("homeSpread") for s in spread]
            sp_home_close_odds = [s.get("currentLine", {}).get("homeOdds") for s in spread]
            sp_away_close_odds = [s.get("currentLine", {}).get("awayOdds") for s in spread]

            rows.append(
                {
                    "game_date": date_str,
                    "away_team": _normalize_team(away_short),
                    "home_team": _normalize_team(home_short),
                    "away_score": view.get("awayTeamScore"),
                    "home_score": view.get("homeTeamScore"),
                    "venue_name": view.get("venueName"),
                    "n_books_total": sum(1 for v in total_close if v is not None),
                    "total_open_median": _safe_median(total_open),
                    "total_close_median": _safe_median(total_close),
                    "over_odds_close_median": _safe_median(over_close),
                    "under_odds_close_median": _safe_median(under_close),
                    "ml_home_open_median": _safe_median(ml_home_open),
                    "ml_away_open_median": _safe_median(ml_away_open),
                    "ml_home_close_median": _safe_median(ml_home_close),
                    "ml_away_close_median": _safe_median(ml_away_close),
                    "spread_home_close_median": _safe_median(sp_home_close),
                    "spread_home_close_odds_median": _safe_median(sp_home_close_odds),
                    "spread_away_close_odds_median": _safe_median(sp_away_close_odds),
                    "source": "sbr_arnav_saraogi",
                }
            )

    out = pd.DataFrame(rows, columns=STANDARD_ODDS_COLUMNS)
    return out.sort_values(["game_date", "home_team"]).reset_index(drop=True)


def match_odds_to_games(odds: pd.DataFrame, games: pd.DataFrame) -> pd.DataFrame:
    """Join market-odds rows to project-standard games by (date, home, away).

    Returns one row per matched odds entry with the canonical game_id attached.
    Multi-game (doubleheader) days are handled best-effort: odds rows without an explicit
    game time can match either game of a double-header, so we keep the first match.
    """

    games_view = games.copy()
    games_view["game_id"] = games_view["game_id"].astype(str)
    games_view["game_date_only"] = pd.to_datetime(games_view["game_date"], utc=True, errors="coerce").dt.tz_convert(
        "America/New_York"
    ).dt.strftime("%Y-%m-%d")

    odds_view = odds.copy()
    odds_view["game_date_only"] = odds_view["game_date"].astype(str).str.slice(0, 10)

    keys = ["game_date_only", "home_team", "away_team"]
    games_dedup = games_view.drop_duplicates(subset=keys, keep="first")
    joined = odds_view.merge(
        games_dedup[["game_id", "game_date", "home_team", "away_team", "game_date_only"]].rename(
            columns={"game_date": "game_date_canonical"}
        ),
        on=keys,
        how="left",
    )

    # Second pass: try the ATH<->OAK alternate name for unmatched rows. SBR rebranded
    # the Athletics to ATH for the entire 2021-2024 historical dump, while our
    # standardized games use OAK before 2025 and ATH from 2025 onward. Same for any
    # other future rebrand we add here.
    rebrand_alts = {"ATH": "OAK", "OAK": "ATH"}

    def _retry(side: str) -> None:
        nonlocal joined
        miss_mask = joined["game_id"].isna() & joined[side].isin(rebrand_alts)
        if not miss_mask.any():
            return
        cols = list(dict.fromkeys([side, "game_date_only", "home_team", "away_team"]))
        retry_view = joined.loc[miss_mask, cols].copy()
        retry_view[side] = retry_view[side].map(lambda v: rebrand_alts.get(v, v))
        retry = retry_view.merge(
            games_dedup[["game_id", "game_date", "home_team", "away_team", "game_date_only"]].rename(
                columns={"game_date": "game_date_canonical"}
            ),
            on=keys,
            how="left",
        )
        joined.loc[miss_mask, "game_id"] = retry["game_id"].to_numpy()
        joined.loc[miss_mask, "game_date_canonical"] = retry["game_date_canonical"].to_numpy()

    _retry("home_team")
    _retry("away_team")
    return joined


def evaluate_predictions_against_market(
    predictions: pd.DataFrame,
    odds: pd.DataFrame,
    *,
    lean_margin: float = 0.5,
    strong_margin: float = 1.5,
) -> pd.DataFrame:
    """Replace the synthetic 8.5 line with each game's real market total close line.

    Inputs:
        predictions: rows from runs_catboost_predictions_*.csv (need game_id, pred_total,
                     actual_total when scored).
        odds: rows from standardized-and-matched market odds (need game_id, total_close_median,
              over_odds_close_median, under_odds_close_median).

    Output: predictions joined with real line, plus market-based ou_pick/ou_correct/ou_margin
            and pass/lean/strong classification.
    """

    odds_view = odds[
        [
            "game_id",
            "total_open_median",
            "total_close_median",
            "over_odds_close_median",
            "under_odds_close_median",
            "n_books_total",
        ]
    ].dropna(subset=["game_id"]).copy()
    odds_view["game_id"] = odds_view["game_id"].astype(str)

    preds = predictions.copy()
    preds["game_id"] = preds["game_id"].astype(str)
    joined = preds.merge(odds_view, on="game_id", how="left", suffixes=("", "_market"))

    joined["market_line"] = joined["total_close_median"]
    joined["market_line_open"] = joined["total_open_median"]
    joined["ou_margin_market"] = joined["pred_total"] - joined["market_line"]

    def _classify(row):
        margin = row.get("ou_margin_market")
        if margin is None or pd.isna(margin) or pd.isna(row.get("market_line")):
            return ("no_line", "no_line")
        abs_m = abs(margin)
        pick = "over" if margin > 0 else "under"
        if abs_m < lean_margin:
            return (pick, "pass")
        if abs_m >= strong_margin:
            return (pick, "strong")
        return (pick, "lean")

    classified = joined.apply(_classify, axis=1, result_type="expand")
    classified.columns = ["ou_pick_market", "ou_confidence_market"]
    joined = pd.concat([joined, classified], axis=1)

    if "actual_total" in joined.columns:
        actual_ou = np.where(
            joined["actual_total"].isna() | joined["market_line"].isna(),
            None,
            np.where(joined["actual_total"] > joined["market_line"], "over",
                     np.where(joined["actual_total"] < joined["market_line"], "under", "push")),
        )
        joined["actual_ou_market"] = actual_ou
        joined["ou_correct_market"] = np.where(
            (joined["ou_pick_market"].isin(["over", "under"]))
            & (joined["actual_ou_market"].isin(["over", "under"])),
            (joined["ou_pick_market"] == joined["actual_ou_market"]).astype(float),
            np.nan,
        )
    return joined


def summarize_market_ou_rules(evaluated: pd.DataFrame) -> pd.DataFrame:
    """Aggregate accuracy by ou_confidence_market bucket on scored, non-pass rows."""

    df = evaluated.copy()
    if "ou_correct_market" not in df.columns:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    for bucket in ["pass", "lean", "strong"]:
        sub = df[df["ou_confidence_market"] == bucket]
        scored = sub.dropna(subset=["ou_correct_market"])
        rows.append(
            {
                "bucket": bucket,
                "n_total": int(len(sub)),
                "n_scored": int(len(scored)),
                "n_hits": int(scored["ou_correct_market"].sum()) if len(scored) else 0,
                "accuracy": float(scored["ou_correct_market"].mean()) if len(scored) else None,
            }
        )
    # actionable = lean + strong
    actionable = df[df["ou_confidence_market"].isin(["lean", "strong"])]
    a_scored = actionable.dropna(subset=["ou_correct_market"])
    rows.append(
        {
            "bucket": "actionable",
            "n_total": int(len(actionable)),
            "n_scored": int(len(a_scored)),
            "n_hits": int(a_scored["ou_correct_market"].sum()) if len(a_scored) else 0,
            "accuracy": float(a_scored["ou_correct_market"].mean()) if len(a_scored) else None,
        }
    )
    return pd.DataFrame(rows)
