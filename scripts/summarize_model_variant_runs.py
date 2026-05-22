"""Combine mean model-test outputs from several experiment directories."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from mlb_winprob.data_sources import write_csv_table


def markdown_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return "_No rows._"
    lines = [
        "| " + " | ".join(map(str, frame.columns)) + " |",
        "| " + " | ".join("---" for _ in frame.columns) + " |",
    ]
    for _, row in frame.iterrows():
        lines.append("| " + " | ".join("" if pd.isna(value) else str(value) for value in row.tolist()) + " |")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", nargs="+", required=True, help="variant=path/to/experiment_dir")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    rows = []
    for item in args.runs:
        variant, path = item.split("=", 1)
        frame = pd.read_csv(Path(path) / "mean_by_model.csv")
        frame.insert(0, "feature_variant", variant)
        rows.append(frame)

    summary = pd.concat(rows, ignore_index=True).sort_values(
        ["mean_log_loss", "mean_brier_score", "feature_variant", "model_name"]
    )
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    write_csv_table(summary, output / "mean_by_variant_model.csv")

    top = summary.head(5).copy()
    lines = [
        "# Model Variant Comparison",
        "",
        "## Mean By Variant And Model",
        "",
        markdown_table(summary),
        "",
        "## Top 5 By Log Loss",
        "",
        markdown_table(top),
        "",
    ]
    (output / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote model variant comparison to {output}")


if __name__ == "__main__":
    main()
