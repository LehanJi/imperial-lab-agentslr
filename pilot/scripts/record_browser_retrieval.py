#!/usr/bin/env python3
"""Record the single browser-rendered PMC fallback in the pilot manifest."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "pilot/workspace/agentslr/harvests/lassa/pilot_sample_downloads.csv"
PDF_PATH = ROOT / "pilot/workspace/agentslr/harvests/lassa/pilot_pdfs/PMID_25404077.pdf"
SAMPLE_ID = "LASSA-011"


def main() -> None:
    if not PDF_PATH.is_file() or PDF_PATH.read_bytes()[:4] != b"%PDF":
        raise SystemExit(f"Expected PDF is missing or invalid: {PDF_PATH}")

    df = pd.read_csv(CSV_PATH)
    mask = df["sample_id"].eq(SAMPLE_ID)
    if mask.sum() != 1:
        raise SystemExit(f"Expected exactly one {SAMPLE_ID} row; found {mask.sum()}")

    df.loc[mask, "downloaded"] = True
    df.loc[mask, "downloaded_path"] = str(PDF_PATH)
    df.loc[mask, "download_attempted_at"] = datetime.now(timezone.utc).isoformat()
    df.loc[mask, "download_source"] = "PMC_browser_print_to_PDF"
    df.loc[mask, "download_error"] = ""
    df.to_csv(CSV_PATH, index=False)
    print(f"Recorded {SAMPLE_ID}: {PDF_PATH}")


if __name__ == "__main__":
    main()
