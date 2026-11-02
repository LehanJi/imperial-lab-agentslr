#!/usr/bin/env python3
"""Prepare the pre-registered 10-paper parameter extraction subset without gold values."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


GOLD_OR_STRATIFICATION_COLUMNS = {
    "perg_fulltext_result",
    "perg_abstract_result",
    "perg_subset",
    "Covidence #",
    "covidence_id",
    "stratum_code",
    "stratum_description",
    "parameter_gold_records",
    "parameter_classes",
    "model_gold_records",
    "outbreak_gold_records",
    "any_extraction_gold",
    "abstract_screening_gold",
    "fulltext_screening_gold",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--screening-results", type=Path, required=True)
    parser.add_argument("--sample-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    screening = pd.read_csv(args.screening_results)
    manifest = pd.read_csv(args.sample_manifest)
    selected_ids = set(
        manifest.loc[
            manifest["stratum_code"].eq("A_parameter_gold"), "article_id"
        ].astype(str)
    )
    subset = screening[screening["article_id"].astype(str).isin(selected_ids)].copy()
    subset = subset.drop(
        columns=[
            column
            for column in GOLD_OR_STRATIFICATION_COLUMNS
            if column in subset.columns
        ]
    )
    if "sample_order" in subset.columns:
        subset = subset.sort_values("sample_order", kind="stable")

    leaked = GOLD_OR_STRATIFICATION_COLUMNS.intersection(subset.columns)
    if leaked:
        raise RuntimeError(f"Gold-label leakage detected: {sorted(leaked)}")
    if len(subset) != 10 or subset["article_id"].nunique() != 10:
        raise ValueError("Expected exactly 10 unique parameter-gold pilot papers")
    if subset["markdown_content"].isna().any():
        raise ValueError("At least one selected paper has no Markdown full text")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    subset.to_csv(args.output, index=False)
    print(f"Wrote {len(subset)} blinded extraction rows to {args.output}")
    print(f"Gold/stratification columns present: {sorted(leaked)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
