#!/usr/bin/env python3
"""Create a leakage-resistant full-text screening input for the Lassa pilot."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


GOLD_COLUMNS = {
    "perg_fulltext_result",
    "perg_abstract_result",
    "perg_subset",
    "Covidence #",
    "covidence_id",
    "stratum_code",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dataframe = pd.read_csv(args.input)
    missing = {"article_id", "title", "markdown_content"} - set(dataframe.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    blinded = dataframe.drop(
        columns=[column for column in GOLD_COLUMNS if column in dataframe.columns]
    ).copy()
    if "sample_order" in blinded.columns:
        blinded = blinded.sort_values("sample_order", kind="stable")

    leaked = GOLD_COLUMNS.intersection(blinded.columns)
    if leaked:
        raise RuntimeError(f"Gold-label leakage detected: {sorted(leaked)}")
    if len(blinded) != 20 or blinded["article_id"].nunique() != 20:
        raise ValueError("Expected exactly 20 unique pilot articles")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    blinded.to_csv(args.output, index=False)
    print(f"Wrote {len(blinded)} blinded rows to {args.output}")
    print(f"Columns: {len(blinded.columns)}; gold columns present: {sorted(leaked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
