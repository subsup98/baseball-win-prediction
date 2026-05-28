"""Parse saved ProEyeKyuu game HTML pages into table/link CSVs.

This is intentionally local-only. It resumes by skipping pages that already
have the final box-score table and links output.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from mlb_winprob.data_sources import ProEyeKyuuCollector


def _is_complete(output_dir: Path, stem: str) -> bool:
    return (output_dir / f"{stem}_table_16.csv").exists() and (output_dir / f"{stem}_links.csv").exists()


def _parse_one(args: tuple[str, str]) -> int:
    html_path_raw, output_dir_raw = args
    html_path = Path(html_path_raw)
    output_dir = Path(output_dir_raw)
    if _is_complete(output_dir, html_path.stem):
        return 0

    html = html_path.read_text(encoding="utf-8")
    outputs = 0
    for index, table in enumerate(ProEyeKyuuCollector.extract_static_html_tables(html), start=1):
        table.to_csv(output_dir / f"{html_path.stem}_table_{index}.csv", index=False)
        outputs += 1
    links = ProEyeKyuuCollector.extract_links(html)
    if not links.empty:
        links.to_csv(output_dir / f"{html_path.stem}_links.csv", index=False)
        outputs += 1
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--progress-every", type=int, default=250)
    args = parser.parse_args()

    pages_dir = Path(args.pages_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = sorted(pages_dir.glob("*_game.html"))
    remaining = [page for page in pages if not _is_complete(output_dir, page.stem)]
    print(f"pages={len(pages)} remaining={len(remaining)} workers={args.workers}", flush=True)

    done = 0
    outputs = 0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(_parse_one, (str(page), str(output_dir))) for page in remaining]
        for future in as_completed(futures):
            outputs += future.result()
            done += 1
            if done % args.progress_every == 0:
                print(f"progress={done}/{len(remaining)} outputs={outputs}", flush=True)

    complete = sum(1 for page in pages if _is_complete(output_dir, page.stem))
    print(f"done={done} outputs={outputs} complete={complete}/{len(pages)}", flush=True)


if __name__ == "__main__":
    main()
