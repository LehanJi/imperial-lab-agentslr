#!/usr/bin/env python3
"""Download the AgentSLR Hugging Face dataset into the local harness layout."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from huggingface_hub import hf_hub_download


REPO_ID = "OxRML/AgentSLR"

PATHOGEN_TITLE = {
    "marburg": "Marburg",
    "ebola": "Ebola",
    "lassa": "Lassa",
    "sars": "SARS",
    "zika": "Zika",
    "mers": "MERS",
    "nipah": "Nipah",
}

EXTRACTION_FILES = {
    "parameter_extractions_ebola/ebola.parquet": "perg/extracted/ebola_parameters.csv",
    "parameter_extractions_lassa/lassa.parquet": "perg/extracted/lassa_parameters.csv",
    "parameter_extractions_sars/sars.parquet": "perg/extracted/sars_parameters.csv",
    "parameter_extractions_zika/zika.parquet": "perg/extracted/zika_parameters.csv",
    "transmission_model_extractions_ebola/ebola.parquet": "perg/extracted/ebola_models.csv",
    "transmission_model_extractions_lassa/lassa.parquet": "perg/extracted/lassa_models.csv",
    "transmission_model_extractions_sars/sars.parquet": "perg/extracted/sars_models.csv",
    "transmission_model_extractions_zika/zika.parquet": "perg/extracted/zika_models.csv",
    "outbreak_extractions_lassa/lassa.parquet": "perg/extracted/lassa_outbreaks.csv",
    "outbreak_extractions_zika/zika.parquet": "perg/extracted/zika_outbreaks.csv",
}


def selected_extraction_files(pathogens: list[str]) -> dict[str, str]:
    if set(pathogens) == set(PATHOGEN_TITLE):
        return EXTRACTION_FILES
    pathogen_prefixes = tuple(f"perg/extracted/{pathogen}_" for pathogen in pathogens)
    return {
        repo_path: target
        for repo_path, target in EXTRACTION_FILES.items()
        if target.startswith(pathogen_prefixes)
    }


def download_parquet(
    repo_id: str,
    repo_path: str,
    local_dir: Path | None = None,
) -> pd.DataFrame:
    if local_dir is not None:
        local_path = local_dir / "data" / repo_path
        if not local_path.exists():
            raise FileNotFoundError(
                f"Expected Hugging Face file not found: {local_path}. "
                "Download the dataset with huggingface_hub.snapshot_download first or omit --hf-local-dir."
            )
        return pd.read_parquet(local_path)

    local_path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        filename=f"data/{repo_path}",
    )
    return pd.read_parquet(local_path)


def write_csv(dataframe: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False)


def write_harvest_and_screening(
    pathogen: str,
    dataframe: pd.DataFrame,
    output_root: Path,
) -> None:
    harvest = dataframe.copy()
    if "Covidence #" not in harvest.columns and "covidence_id" in harvest.columns:
        harvest["Covidence #"] = harvest["covidence_id"]
    if "downloaded" in harvest.columns:
        harvest["downloaded"] = False
    if "downloaded_path" in harvest.columns:
        harvest["downloaded_path"] = pd.NA
    if "download_source" in harvest.columns:
        harvest["download_source"] = pd.NA
    if "download_error" in harvest.columns:
        harvest["download_error"] = pd.NA

    harvest_path = output_root / "agentslr" / "harvests" / pathogen / "harvest_metadata.csv"
    write_csv(harvest, harvest_path)

    screening = pd.DataFrame(
        {
            "Title": dataframe.get("title", pd.Series(dtype=object)),
            "Authors": dataframe.get("authors", pd.Series(dtype=object)),
            "Abstract": dataframe.get("abstract", pd.Series(dtype=object)),
            "Published Year": dataframe.get("year", pd.Series(dtype=object)),
            "Journal": dataframe.get("journal", pd.Series(dtype=object)),
            "DOI": dataframe.get("doi", pd.Series(dtype=object)),
            "Covidence #": dataframe.get("covidence_id", pd.Series(dtype=object)),
            "perg_abstract_result": dataframe.get("perg_abstract_result", pd.Series(dtype=object)),
            "perg_fulltext_result": dataframe.get("perg_fulltext_result", pd.Series(dtype=object)),
        }
    )
    screening_path = output_root / "perg" / "screening" / f"{PATHOGEN_TITLE[pathogen]}_filtered.csv"
    write_csv(screening, screening_path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=REPO_ID)
    parser.add_argument(
        "--hf-local-dir",
        type=Path,
        default=None,
        help="Read parquet files from a local Hugging Face dataset download instead of fetching them.",
    )
    parser.add_argument("--output-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--pathogen",
        choices=[*PATHOGEN_TITLE.keys(), "all"],
        default="all",
    )
    parser.add_argument("--skip-extractions", action="store_true")
    args = parser.parse_args()

    pathogens = list(PATHOGEN_TITLE) if args.pathogen == "all" else [args.pathogen]

    total_rows = 0
    for pathogen in pathogens:
        repo_path = f"harvest_metadata_and_screening/{pathogen}.parquet"
        df = download_parquet(args.repo_id, repo_path, args.hf_local_dir)
        write_harvest_and_screening(pathogen, df, args.output_root)
        total_rows += len(df)
        print(f"{pathogen}: wrote {len(df):,} harvest and screening rows")

    if not args.skip_extractions:
        for repo_path, target in selected_extraction_files(pathogens).items():
            df = download_parquet(args.repo_id, repo_path, args.hf_local_dir)
            write_csv(df, args.output_root / target)
            print(f"{target}: wrote {len(df):,} rows")

    print(f"Done. Harvest rows written: {total_rows:,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
