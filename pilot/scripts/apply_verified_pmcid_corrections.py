#!/usr/bin/env python3
"""Apply auditable PMCID corrections to the 20-paper pilot download manifest."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = (
    ROOT
    / "pilot"
    / "workspace"
    / "agentslr"
    / "harvests"
    / "lassa"
    / "pilot_sample_downloads.csv"
)

# Each PMCID was verified against the DOI/title shown on the linked PMC article page.
CORRECTIONS = {
    "LASSA-001": (
        "PMC4995818",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4995818/",
    ),
    "LASSA-007": (
        "PMC10823436",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10823436/",
    ),
    "LASSA-009": (
        "PMC5468694",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC5468694/",
    ),
    "LASSA-010": (
        "PMC7984835",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC7984835/",
    ),
    "LASSA-011": (
        "PMC4347375",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4347375/",
    ),
    "LASSA-013": (
        "PMC10031424",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC10031424/",
    ),
    "LASSA-016": (
        "PMC8637796",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC8637796/",
    ),
}

# These two PMC records are free to read but have no PDF in the PMC cloud
# dataset. The publisher-hosted PDFs were verified from the DOI/OpenAlex pages.
DIRECT_PDF_OVERRIDES = {
    "LASSA-007": (
        "https://stacks.cdc.gov/view/cdc/147658/cdc_147658_DS1.pdf",
        "https://stacks.cdc.gov/view/cdc/147658",
    ),
    "LASSA-011": (
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4347375/pdf/tropmed-92-172.pdf",
        "https://pmc.ncbi.nlm.nih.gov/articles/PMC4347375/",
    ),
}


def text_or_blank(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    output = args.output or args.input

    dataframe = pd.read_csv(args.input, dtype={"pmcid": object})
    if "sample_id" not in dataframe.columns or "pmcid" not in dataframe.columns:
        raise ValueError("Input must contain sample_id and pmcid columns.")

    unknown = set(CORRECTIONS) - set(dataframe["sample_id"])
    if unknown:
        raise ValueError(f"Correction IDs absent from input: {sorted(unknown)}")

    if "source_pmcid" not in dataframe.columns:
        dataframe["source_pmcid"] = dataframe["pmcid"].map(text_or_blank)
    if "pmcid_correction_source_url" not in dataframe.columns:
        dataframe["pmcid_correction_source_url"] = ""
    if "source_openalex_pdf_url" not in dataframe.columns:
        dataframe["source_openalex_pdf_url"] = dataframe.get(
            "openalex_pdf_url", pd.Series("", index=dataframe.index)
        ).map(text_or_blank)
    if "direct_pdf_url_source" not in dataframe.columns:
        dataframe["direct_pdf_url_source"] = ""
    if "openalex_pdf_url" not in dataframe.columns:
        dataframe["openalex_pdf_url"] = ""
    dataframe["openalex_pdf_url"] = dataframe["openalex_pdf_url"].astype("object")

    for sample_id, (pmcid, source_url) in CORRECTIONS.items():
        mask = dataframe["sample_id"] == sample_id
        dataframe.loc[mask, "pmcid"] = pmcid
        dataframe.loc[mask, "pmcid_correction_source_url"] = source_url

    for sample_id, (pdf_url, source_url) in DIRECT_PDF_OVERRIDES.items():
        mask = dataframe["sample_id"] == sample_id
        dataframe.loc[mask, "openalex_pdf_url"] = pdf_url
        dataframe.loc[mask, "direct_pdf_url_source"] = source_url

    output.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output, index=False, lineterminator="\n")
    print(
        f"Applied {len(CORRECTIONS)} verified PMCID corrections and "
        f"{len(DIRECT_PDF_OVERRIDES)} direct-PDF overrides to {output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
