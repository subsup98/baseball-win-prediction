"""Collect Baseball Savant / Statcast event CSVs in parallel chunks.

The script derives each season range from standardized MLB Stats API games.csv
files, downloads small date chunks with pybaseball, then writes both chunk CSVs
and combined season CSVs.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import time

import pandas as pd


@dataclass(frozen=True)
class Chunk:
    season: int
    start_date: str
    end_date: str
    output: Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", default="2021,2022,2023,2024,2025")
    parser.add_argument("--standardized-root", default="data/standardized")
    parser.add_argument("--output-root", default="data/raw/statcast")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--chunk-days", type=int, default=7)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def season_ranges(seasons: list[int], standardized_root: Path) -> dict[int, tuple[pd.Timestamp, pd.Timestamp]]:
    ranges: dict[int, tuple[pd.Timestamp, pd.Timestamp]] = {}
    for season in seasons:
        games_path = standardized_root / f"mlb_stats_api_{season}" / "games.csv"
        games = pd.read_csv(games_path, parse_dates=["game_date"])
        ranges[season] = (games["game_date"].min().normalize(), games["game_date"].max().normalize())
    return ranges


def make_chunks(
    ranges: dict[int, tuple[pd.Timestamp, pd.Timestamp]],
    output_root: Path,
    chunk_days: int,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    chunk_root = output_root / "chunks"
    for season, (start, end) in ranges.items():
        cursor = start
        while cursor <= end:
            chunk_end = min(cursor + pd.Timedelta(days=chunk_days - 1), end)
            start_text = cursor.strftime("%Y-%m-%d")
            end_text = chunk_end.strftime("%Y-%m-%d")
            output = chunk_root / f"statcast_{season}_{start_text}_{end_text}.csv"
            chunks.append(Chunk(season, start_text, end_text, output))
            cursor = chunk_end + pd.Timedelta(days=1)
    return chunks


def collect_chunk(chunk: Chunk, force: bool) -> tuple[Chunk, int, str]:
    if chunk.output.exists() and chunk.output.stat().st_size > 0 and not force:
        try:
            rows = sum(1 for _ in chunk.output.open("r", encoding="utf-8", errors="ignore")) - 1
        except OSError:
            rows = -1
        return chunk, max(rows, 0), "skipped"

    import pybaseball

    chunk.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    frame = pybaseball.statcast(start_dt=chunk.start_date, end_dt=chunk.end_date)
    frame.to_csv(chunk.output, index=False)
    elapsed = time.monotonic() - started
    return chunk, len(frame), f"downloaded in {elapsed:.1f}s"


def combine_seasons(seasons: list[int], output_root: Path) -> None:
    chunk_root = output_root / "chunks"
    for season in seasons:
        paths = sorted(chunk_root.glob(f"statcast_{season}_*.csv"))
        frames = [pd.read_csv(path, low_memory=False) for path in paths if path.stat().st_size > 0]
        if not frames:
            continue
        combined = pd.concat(frames, ignore_index=True)
        if {"game_pk", "pitch_number", "at_bat_number"}.issubset(combined.columns):
            combined = combined.drop_duplicates(subset=["game_pk", "at_bat_number", "pitch_number"])
        combined.to_csv(output_root / f"statcast_{season}.csv", index=False)
        print(f"combined {season}: {len(combined)} rows from {len(paths)} chunks")


def main() -> None:
    args = parse_args()
    seasons = [int(value.strip()) for value in args.seasons.split(",") if value.strip()]
    output_root = Path(args.output_root)
    ranges = season_ranges(seasons, Path(args.standardized_root))
    chunks = make_chunks(ranges, output_root, args.chunk_days)
    print(f"collecting {len(chunks)} chunks with {args.workers} workers")
    for season, (start, end) in ranges.items():
        print(f"{season}: {start.date()} to {end.date()}")

    failed_path = output_root / "statcast_failed_chunks.csv"
    failures: list[tuple[Chunk, str]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(collect_chunk, chunk, args.force): chunk for chunk in chunks}
        for future in as_completed(futures):
            chunk = futures[future]
            try:
                completed_chunk, rows, status = future.result()
                print(f"{completed_chunk.season} {completed_chunk.start_date}..{completed_chunk.end_date}: {rows} rows {status}")
            except Exception as exc:  # noqa: BLE001 - keep long collection resumable.
                failures.append((chunk, str(exc)))
                print(f"FAILED {chunk.season} {chunk.start_date}..{chunk.end_date}: {exc}")

    if failures:
        pd.DataFrame(
            [
                {
                    "season": chunk.season,
                    "start_date": chunk.start_date,
                    "end_date": chunk.end_date,
                    "output": str(chunk.output),
                    "error": error,
                }
                for chunk, error in failures
            ]
        ).to_csv(failed_path, index=False)
        raise SystemExit(f"{len(failures)} chunks failed; see {failed_path}")

    if failed_path.exists():
        failed_path.unlink()
    combine_seasons(seasons, output_root)


if __name__ == "__main__":
    main()
