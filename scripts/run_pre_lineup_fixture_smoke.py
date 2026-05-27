"""Run a fixture-backed pre-lineup ingestion smoke test.

This script wraps existing confirmed lineup rows into a provider-shaped JSON
snapshot, then exercises the same normalization, external ID mapping, and
pre-lineup feature build path used by an automated projected-lineup source.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import BallDontLieMLBCollector, read_csv_table, write_csv_table, write_json
from mlb_winprob.features import FeatureBuilder
from mlb_winprob.id_map import build_external_game_id_map, build_external_player_id_map
from mlb_winprob.schemas import FeatureBuildConfig


def _provider_payload(games: pd.DataFrame, lineups: pd.DataFrame, game_id: str) -> dict:
    game = games[games["game_id"].astype(str) == str(game_id)].iloc[0]
    game_lineups = lineups[lineups["game_id"].astype(str) == str(game_id)].copy()
    payload_rows = []
    for team, team_rows in game_lineups.groupby("team", sort=False):
        payload_rows.append(
            {
                "id": f"lineup-{game_id}-{team}",
                "game": {
                    "id": f"bdl-game-{game_id}",
                    "date": str(game["game_date"]),
                    "home_team": {"abbreviation": game["home_team"]},
                    "away_team": {"abbreviation": game["away_team"]},
                },
                "team": {"abbreviation": team},
                "status": "projected",
                "updated_at": "2025-03-18T03:00:00Z",
                "players": [
                    {
                        "player": {
                            "id": f"bdl-player-{row.player_id}",
                            "full_name": row.player_name,
                            "bats": row.bats,
                        },
                        "batting_order": int(row.batting_order),
                    }
                    for row in team_rows.sort_values("batting_order").itertuples(index=False)
                ],
            }
        )
    return {"data": payload_rows, "meta": {"fixture": True}}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--standardized-dir", default="data/standardized/mlb_stats_api_2025")
    parser.add_argument("--id-map", default="data/processed/id_map.csv")
    parser.add_argument("--game-id", default="778563")
    parser.add_argument("--output-dir", default="outputs/pre_lineup_fixture_smoke")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    standardized = Path(args.standardized_dir)
    output_dir = Path(args.output_dir)
    raw_dir = output_dir / "raw"
    standardized_dir = output_dir / "standardized"
    metadata_dir = output_dir / "metadata"
    processed_dir = output_dir / "processed"
    for path in [raw_dir, standardized_dir, metadata_dir, processed_dir]:
        path.mkdir(parents=True, exist_ok=True)

    games = read_csv_table(standardized / "games.csv")
    lineups = read_csv_table(standardized / "lineups.csv")
    payload = _provider_payload(games, lineups, str(args.game_id))
    raw_json = write_json(payload, raw_dir / "balldontlie_lineups_fixture.json")

    normalized_unmapped = BallDontLieMLBCollector.normalize_lineups(
        payload,
        captured_at="2025-03-18T03:00:00Z",
        prediction_mode="projected",
    )
    unmapped_path = standardized_dir / "lineups_unmapped.csv"
    write_csv_table(normalized_unmapped, unmapped_path)

    game_map = build_external_game_id_map(normalized_unmapped, games)
    player_map = build_external_player_id_map(normalized_unmapped, read_csv_table(args.id_map), season=2025)
    game_map_path = metadata_dir / "balldontlie_game_id_map.csv"
    player_map_path = metadata_dir / "balldontlie_player_id_map.csv"
    write_csv_table(game_map, game_map_path)
    write_csv_table(player_map, player_map_path)

    normalized = BallDontLieMLBCollector.normalize_lineups(
        payload,
        captured_at="2025-03-18T03:00:00Z",
        prediction_mode="projected",
        game_id_map=game_map,
        player_id_map=player_map,
    )
    projected_lineups_path = standardized_dir / "lineups_projected.csv"
    write_csv_table(normalized, projected_lineups_path)

    game_filter = games["game_id"].astype(str) == str(args.game_id)
    feature_builder = FeatureBuilder(FeatureBuildConfig(prediction_mode="pre_lineup"))
    features = feature_builder.build(
        games=games[game_filter].copy(),
        batting_logs=read_csv_table(standardized / "batting_logs.csv"),
        pitcher_logs=read_csv_table(standardized / "pitcher_logs.csv"),
        lineups=normalized,
        weather=read_csv_table(standardized / "weather.csv"),
    )
    feature_path = processed_dir / "features_pre_lineup_fixture.csv"
    write_csv_table(features, feature_path)

    summary = pd.DataFrame(
        [
            {"metric": "raw_json", "value": str(raw_json)},
            {"metric": "unmapped_lineup_rows", "value": len(normalized_unmapped)},
            {"metric": "mapped_game_rows", "value": len(game_map)},
            {"metric": "mapped_player_rows", "value": len(player_map)},
            {"metric": "mapped_lineup_rows", "value": len(normalized)},
            {"metric": "feature_rows", "value": len(features)},
            {
                "metric": "lineup_player_count_non_null",
                "value": int(features["home_lineup_player_count"].notna().sum() + features["away_lineup_player_count"].notna().sum()),
            },
        ]
    )
    summary_path = output_dir / "summary.csv"
    write_csv_table(summary, summary_path)
    print(summary.to_string(index=False))
    print(f"Wrote summary: {summary_path}")
    print(f"Wrote pre-lineup features: {feature_path}")


if __name__ == "__main__":
    main()
