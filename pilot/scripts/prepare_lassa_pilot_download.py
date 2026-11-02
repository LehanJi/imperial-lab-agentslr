#!/usr/bin/env python3
"""Prepare the 20-paper metadata input for AgentSLR's download-only stage."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE = ROOT / "pilot" / "data" / "lassa_pilot_sample.csv"
DEFAULT_METADATA = (
    ROOT
    / "pilot"
    / "workspace"
    / "agentslr"
    / "harvests"
    / "lassa"
    / "harvest_metadata.csv"
)
DEFAULT_OUTPUT = (
    ROOT
    / "pilot"
    / "workspace"
    / "agentslr"
    / "harvests"
    / "lassa"
    / "pilot_sample_metadata_input.csv"
)


def normalise_covidence(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip().str.removeprefix("#")
    return pd.to_numeric(values, errors="coerce").astype("Int64")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    sample = pd.read_csv(args.sample)
    metadata = pd.read_csv(args.metadata)
    sample["covidence_id_normalised"] = normalise_covidence(sample["covidence_id"])
    metadata["covidence_id_normalised"] = normalise_covidence(metadata["covidence_id"])

    if len(sample) != 20 or sample["covidence_id_normalised"].duplicated().any():
        raise ValueError("Sample manifest must contain 20 unique Covidence IDs.")
    if metadata["covidence_id_normalised"].duplicated().any():
        raise ValueError("Harvest metadata contain duplicate Covidence IDs.")

    metadata_by_id = metadata.set_index("covidence_id_normalised", drop=False)
    missing = set(sample["covidence_id_normalised"]) - set(metadata_by_id.index)
    if missing:
        raise ValueError(f"Selected IDs missing from harvest metadata: {sorted(missing)}")

    ordered = metadata_by_id.loc[sample["covidence_id_normalised"].tolist()].copy().reset_index(drop=True)
    ordered.insert(0, "sample_id", sample["sample_id"].tolist())
    ordered.insert(1, "sample_order", sample["sample_order"].astype(int).tolist())
    ordered.insert(2, "stratum_code", sample["stratum_code"].tolist())
    ordered["downloaded"] = False
    ordered["downloaded_path"] = pd.NA
    ordered["download_attempted_at"] = pd.NA
    ordered["download_source"] = pd.NA
    ordered["download_error"] = pd.NA
    ordered = ordered.drop(columns=["covidence_id_normalised"])

    if ordered["doi"].isna().any() or ordered["title"].isna().any():
        raise ValueError("Every selected paper must have a DOI and title.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    ordered.to_csv(args.output, index=False, lineterminator="\n")
    print(f"Wrote {len(ordered)} rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
