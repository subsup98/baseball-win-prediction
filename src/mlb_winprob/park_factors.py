"""Park factor helpers built from already-standardized game logs."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from mlb_winprob.data_sources import read_csv_table


def build_empirical_park_factors(
    standardized_dirs: list[str | Path],
    *,
    lag_seasons: int = 1,
    min_games: int = 20,
) -> pd.DataFrame:
    """Estimate run/HR park factors from prior standardized seasons.

    The returned ``season`` is the season where the factor should be applied.
    With the default one-season lag, 2021 venue results become 2022 factors.
    This avoids using final same-season park results as pre-game features.
    """

    pieces = []
    for directory in standardized_dirs:
        root = Path(directory)
        games_path = root / "games.csv"
        batting_path = root / "batting_logs.csv"
        if not games_path.exists() or not batting_path.exists():
            continue

        games = read_csv_table(games_path)
        batting = read_csv_table(batting_path)
        required_game_columns = {"game_id", "season", "venue_id", "venue_name", "home_score", "away_score"}
        if not required_game_columns.issubset(games.columns):
            missing = sorted(required_game_columns - set(games.columns))
            raise ValueError(f"{games_path} is missing columns: {missing}")
        if "home_runs" not in batting.columns:
            raise ValueError(f"{batting_path} is missing columns: ['home_runs']")

        game_hr = (
            batting.assign(home_runs=pd.to_numeric(batting["home_runs"], errors="coerce").fillna(0.0))
            .groupby("game_id", as_index=False)["home_runs"]
            .sum()
            .rename(columns={"home_runs": "game_home_runs"})
        )
        games = games.merge(game_hr, on="game_id", how="left")
        games["game_home_runs"] = games["game_home_runs"].fillna(0.0)
        games["total_runs"] = (
            pd.to_numeric(games["home_score"], errors="coerce")
            + pd.to_numeric(games["away_score"], errors="coerce")
        )
        games = games.dropna(subset=["season", "venue_id", "total_runs"])
        pieces.append(games[["game_id", "season", "venue_id", "venue_name", "total_runs", "game_home_runs"]])

    if not pieces:
        return pd.DataFrame(
            columns=[
                "venue_id",
                "venue_name",
                "season",
                "source_season",
                "source_games",
                "park_factor_run",
                "park_factor_hr",
                "source",
            ]
        )

    games = pd.concat(pieces, ignore_index=True)
    games["season"] = pd.to_numeric(games["season"], errors="coerce").astype(int)

    league = (
        games.groupby("season", as_index=False)
        .agg(
            league_games=("game_id", "nunique"),
            league_runs=("total_runs", "sum"),
            league_home_runs=("game_home_runs", "sum"),
        )
    )
    league["league_runs_per_game"] = league["league_runs"] / league["league_games"]
    league["league_hr_per_game"] = league["league_home_runs"] / league["league_games"]

    venue = (
        games.groupby(["season", "venue_id", "venue_name"], as_index=False)
        .agg(
            source_games=("game_id", "nunique"),
            venue_runs=("total_runs", "sum"),
            venue_home_runs=("game_home_runs", "sum"),
        )
    )
    venue = venue.merge(league[["season", "league_runs_per_game", "league_hr_per_game"]], on="season", how="left")
    venue["venue_runs_per_game"] = venue["venue_runs"] / venue["source_games"]
    venue["venue_hr_per_game"] = venue["venue_home_runs"] / venue["source_games"]
    venue["park_factor_run"] = venue["venue_runs_per_game"] / venue["league_runs_per_game"]
    venue["park_factor_hr"] = np.divide(
        venue["venue_hr_per_game"],
        venue["league_hr_per_game"],
        out=np.full(len(venue), np.nan, dtype=float),
        where=venue["league_hr_per_game"].to_numpy(dtype=float) > 0,
    )
    venue = venue[venue["source_games"] >= min_games].copy()
    venue["source_season"] = venue["season"]
    venue["season"] = venue["source_season"] + lag_seasons
    venue["source"] = f"empirical_previous_{lag_seasons}_season"

    return venue[
        [
            "venue_id",
            "venue_name",
            "season",
            "source_season",
            "source_games",
            "park_factor_run",
            "park_factor_hr",
            "source",
        ]
    ].sort_values(["season", "venue_id"]).reset_index(drop=True)
