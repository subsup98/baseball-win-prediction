"""Predict KBO games for a target date with the KBO win model.

Builds a feature table that includes the target date's scheduled games on top of
the season-to-date history, then scores them with a saved KBO model bundle.

For not-yet-played games there is no official starter or lineup, so SP and lineup
features are left missing (the model imputes them); the prediction is driven by
team season-to-date form, recent win rate, and bullpen state.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from mlb_winprob.data_sources import (
    MYKBO_STATS_BASE_URL,
    MyKBOStatsCollector,
    read_csv_table,
    write_csv_table,
)
from mlb_winprob.features import FeatureBuildConfig, FeatureBuilder
from mlb_winprob.kbo import build_kbo_weather_stub, enrich_kbo_games_with_venues, kbo_venue_seed


def fetch_probable_starters(target: pd.DataFrame) -> dict[str, tuple[str, str]]:
    """Map game_id -> (away_sp_id, home_sp_id) from MyKBO preview pages.

    The preview page lists exactly the two probable starters as /players/ links,
    away pitcher first, then home pitcher. Batting lineups are not posted pre-game.
    """

    collector = MyKBOStatsCollector()
    starters: dict[str, tuple[str, str]] = {}
    for _, row in target.iterrows():
        href = row.get("source_href")
        if not isinstance(href, str) or not href:
            continue
        try:
            html = collector.fetch_url(MYKBO_STATS_BASE_URL + href)
        except Exception as exc:  # noqa: BLE001 - skip a game we cannot fetch
            print(f"  {row['game_id']}: fetch failed ({exc})")
            continue
        links = re.findall(r'href="/players/(\d+)-', html)
        # de-dup preserving order
        seen: list[str] = []
        for pid in links:
            if pid not in seen:
                seen.append(pid)
        if len(seen) >= 2:
            starters[str(row["game_id"])] = (seen[0], seen[1])
            print(f"  {row['game_id']} {row['away_team']}@{row['home_team']}: away_sp={seen[0]} home_sp={seen[1]}")
        else:
            print(f"  {row['game_id']}: only {len(seen)} probable starter link(s) found")
    return starters


def build_games(schedule: pd.DataFrame, pitcher_logs: pd.DataFrame, target_date: str, use_probable_starters: bool = False):
    cols = ["game_id", "game_date", "season", "home_team", "away_team", "home_score", "away_score", "home_team_win"]
    for optional_column in ["venue_id", "venue_name"]:
        if optional_column in schedule.columns:
            cols.append(optional_column)

    final = schedule[schedule["is_final"] == 1].dropna(subset=["home_team", "away_team", "home_score", "away_score"])
    final = final[cols].drop_duplicates("game_id", keep="first").copy()

    starters = pitcher_logs[pitcher_logs["is_start"] == 1][["game_id", "team", "player_id"]].drop_duplicates(
        ["game_id", "team"], keep="first"
    )
    final = final.merge(starters.rename(columns={"team": "home_team", "player_id": "home_sp_id"}), on=["game_id", "home_team"], how="left")
    final = final.merge(starters.rename(columns={"team": "away_team", "player_id": "away_sp_id"}), on=["game_id", "away_team"], how="left")
    final = final.drop_duplicates("game_id", keep="first")

    target = schedule[schedule["game_date"] == target_date].copy()
    target = target[~target["game_id"].isin(final["game_id"])]
    keep = ["game_id", "game_date", "season", "home_team", "away_team"]
    for optional_column in ["venue_id", "venue_name"]:
        if optional_column in target.columns:
            keep.append(optional_column)
    if "source_href" in target.columns:
        keep.append("source_href")
    target = target[keep].copy()
    for c in ["home_score", "away_score", "home_team_win"]:
        target[c] = np.nan
    for c in ["home_sp_id", "away_sp_id"]:
        target[c] = pd.Series([pd.NA] * len(target), index=target.index, dtype="string")

    probable = fetch_probable_starters(target) if use_probable_starters else {}
    for gid, (away_sp, home_sp) in probable.items():
        mask = target["game_id"] == gid
        target.loc[mask, "away_sp_id"] = away_sp
        target.loc[mask, "home_sp_id"] = home_sp

    target = target[[c for c in target.columns if c != "source_href"]]
    games = pd.concat([final, target], ignore_index=True)
    for c in ["home_sp_id", "away_sp_id"]:
        games[c] = games[c].astype("string")
    return games, sorted(target["game_id"].tolist()), probable


def project_lineups_from_last_game(
    lineups: pd.DataFrame,
    games: pd.DataFrame,
    target_ids: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    target_games = games[games["game_id"].isin(target_ids)].copy()
    if target_games.empty:
        return lineups, pd.DataFrame()
    historical = lineups.copy()
    historical["game_date"] = pd.to_datetime(historical["game_date"], errors="coerce")
    historical["batting_order"] = pd.to_numeric(historical["batting_order"], errors="coerce")
    historical = historical[historical["batting_order"].between(1, 9)].copy()
    projected_rows = []
    summary_rows = []
    for _, game in target_games.iterrows():
        target_date = pd.to_datetime(game["game_date"], errors="coerce")
        for side in ["away", "home"]:
            team = game[f"{side}_team"]
            team_lineups = historical[
                historical["team"].eq(team)
                & historical["game_date"].lt(target_date)
            ].copy()
            if team_lineups.empty:
                summary_rows.append({"game_id": game["game_id"], "team": team, "projected_rows": 0, "source_game_id": pd.NA})
                continue
            source_game_id = (
                team_lineups.sort_values(["game_date", "game_id"])
                .drop_duplicates("game_id", keep="last")
                .iloc[-1]["game_id"]
            )
            projected = team_lineups[team_lineups["game_id"].eq(source_game_id)].copy()
            projected = projected.sort_values("batting_order").drop_duplicates("batting_order", keep="first").head(9)
            projected["game_id"] = game["game_id"]
            projected["game_date"] = game["game_date"]
            projected["season"] = game["season"]
            projected["prediction_mode"] = "projected"
            projected["lineup_source"] = "last_confirmed_lineup"
            projected["lineup_confidence"] = 0.75
            projected_rows.append(projected)
            summary_rows.append(
                {
                    "game_id": game["game_id"],
                    "team": team,
                    "projected_rows": len(projected),
                    "source_game_id": source_game_id,
                }
            )
    if not projected_rows:
        return lineups, pd.DataFrame(summary_rows)
    projected_lineups = pd.concat(projected_rows, ignore_index=True)
    combined = pd.concat([lineups, projected_lineups], ignore_index=True)
    return combined, pd.DataFrame(summary_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-date", default="2026-05-27")
    parser.add_argument("--canonical-dir", default="data/standardized/kbo/canonical_2021_2026")
    parser.add_argument("--schedule", default="data/standardized/kbo/games_mykbo_schedule_2021_2026.csv")
    parser.add_argument("--model", default="outputs/final_models/kbo_win_random_forest_shallow_2021_2026_env_public_proxy/best_model.joblib")
    parser.add_argument("--venues", default="data/standardized/kbo/venues_seed.csv")
    parser.add_argument("--park-factors", default="data/processed/kbo/park_factors_empirical_kbo_2021_2026.csv")
    parser.add_argument("--output", default="outputs/kbo_predictions/kbo_predictions_2026-05-27.csv")
    parser.add_argument("--probable-starters", action="store_true", help="Fetch probable starters from MyKBO preview pages and inject them.")
    parser.add_argument("--project-lineups", action="store_true", help="Project today's batting order from each team's latest confirmed 1-9 lineup.")
    args = parser.parse_args()

    schedule = read_csv_table(args.schedule)
    schedule["game_id"] = schedule["game_id"].astype("string")
    schedule["game_date"] = pd.to_datetime(schedule["game_date"], errors="coerce").dt.strftime("%Y-%m-%d")
    venues = read_csv_table(args.venues) if Path(args.venues).exists() else kbo_venue_seed()
    schedule = enrich_kbo_games_with_venues(schedule, venues)
    park_factors = read_csv_table(args.park_factors) if Path(args.park_factors).exists() else None

    canonical = Path(args.canonical_dir)
    batting_logs = read_csv_table(canonical / "batting_logs.csv").rename(columns={"mykbo_player_id": "player_id"})
    pitcher_logs = read_csv_table(canonical / "pitcher_logs.csv").rename(columns={"mykbo_player_id": "player_id"})
    lineups = read_csv_table(canonical / "lineups.csv")
    for frame in (batting_logs, pitcher_logs, lineups):
        frame["game_id"] = frame["game_id"].astype("string")
        if "player_id" in frame.columns:
            frame["player_id"] = pd.to_numeric(frame["player_id"], errors="coerce").astype("Int64").astype("string")

    if args.probable_starters:
        print("fetching probable starters from MyKBO preview pages...")
    games, target_ids, probable = build_games(schedule, pitcher_logs, args.target_date, args.probable_starters)
    games = enrich_kbo_games_with_venues(games, venues)
    weather = build_kbo_weather_stub(games, venues)
    if not target_ids:
        raise SystemExit(f"No scheduled games found for {args.target_date}")
    print(f"target games on {args.target_date}: {len(target_ids)}  (with injected starters: {len(probable)})")

    # Inject a synthetic starting-pitcher appearance for each scheduled game so the
    # FeatureBuilder carries each starter's season-to-date forward onto the future
    # game (no box score exists yet, so the stat columns are left NaN).
    if probable:
        target_games = games[games["game_id"].isin(target_ids)][["game_id", "game_date", "season", "home_team", "away_team"]]
        synthetic = []
        for _, g in target_games.iterrows():
            gid = str(g["game_id"])
            if gid not in probable:
                continue
            away_sp, home_sp = probable[gid]
            synthetic.append({"game_id": gid, "team": g["home_team"], "player_id": home_sp, "game_date": g["game_date"], "season": g["season"], "is_start": 1})
            synthetic.append({"game_id": gid, "team": g["away_team"], "player_id": away_sp, "game_date": g["game_date"], "season": g["season"], "is_start": 1})
        if synthetic:
            syn = pd.DataFrame(synthetic)
            syn["game_id"] = syn["game_id"].astype("string")
            syn["player_id"] = syn["player_id"].astype("string")
            pitcher_logs = pd.concat([pitcher_logs, syn], ignore_index=True)
            print(f"injected {len(syn)} synthetic starter rows for season-to-date carry-forward")

    lineup_projection_summary = pd.DataFrame()
    if args.project_lineups:
        lineups, lineup_projection_summary = project_lineups_from_last_game(lineups, games, target_ids)
        projected_total = int(lineup_projection_summary["projected_rows"].sum()) if not lineup_projection_summary.empty else 0
        print(f"projected {projected_total} lineup rows from latest confirmed team lineups")

    builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="confirmed_lineup"))
    features = builder.build(
        games=games,
        batting_logs=batting_logs,
        pitcher_logs=pitcher_logs,
        lineups=lineups,
        weather=weather,
        park_factors=park_factors,
        venues=venues,
    )
    features = features.drop_duplicates("game_id", keep="first")
    today = features[features["game_id"].isin(target_ids)].copy()
    print(f"built feature rows for target date: {len(today)}")

    bundle = joblib.load(args.model)
    feature_columns = bundle["feature_columns"]
    estimator = bundle["estimator"]
    x = today.reindex(columns=feature_columns)
    x = x.apply(pd.to_numeric, errors="coerce")
    today["home_win_probability"] = estimator.predict_proba(x)[:, 1]
    today["pick"] = np.where(today["home_win_probability"] >= 0.5, today["home_team"], today["away_team"])
    today["confidence"] = np.maximum(today["home_win_probability"], 1 - today["home_win_probability"])
    today["win_pick_rule"] = np.select(
        [today["confidence"] >= 0.60, today["confidence"] >= 0.55], ["strong", "lean"], default="pass"
    )

    today["starters_used"] = today["game_id"].astype(str).isin(probable.keys())
    today["lineups_projected"] = args.project_lineups
    out_cols = ["game_id", "game_date", "away_team", "home_team", "home_win_probability", "pick", "confidence", "win_pick_rule", "starters_used"]
    out_cols.append("lineups_projected")
    result = today[out_cols].sort_values("game_id").reset_index(drop=True)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    write_csv_table(result, output)
    if not lineup_projection_summary.empty:
        write_csv_table(lineup_projection_summary, output.with_name(output.stem + "_lineup_sources.csv"))

    print(f"\n=== KBO predictions {args.target_date} (team-form based; no official lineups yet) ===")
    with pd.option_context("display.width", 160):
        show = result.copy()
        show["home_win_probability"] = show["home_win_probability"].round(3)
        show["confidence"] = show["confidence"].round(3)
        print(show.to_string(index=False))
    print(f"\nwrote -> {output}")
    if not lineup_projection_summary.empty:
        print(f"lineup sources -> {output.with_name(output.stem + '_lineup_sources.csv')}")


if __name__ == "__main__":
    main()
