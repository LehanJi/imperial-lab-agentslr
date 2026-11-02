#!/usr/bin/env python3
"""Create the reproducible 20-paper Lassa pilot sample manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "pilot" / "workspace" / "hf" / "AgentSLR" / "data"
AUDIT_PATH = ROOT / "pilot" / "data" / "lassa_dataset_audit.json"
DEFAULT_OUTPUT = ROOT / "pilot" / "data" / "lassa_pilot_sample.csv"
SEED = 20261024

SOURCE_FILES = {
    "screening": WORKSPACE / "harvest_metadata_and_screening" / "lassa.parquet",
    "parameters": WORKSPACE / "parameter_extractions_lassa" / "lassa.parquet",
    "models": WORKSPACE / "transmission_model_extractions_lassa" / "lassa.parquet",
    "outbreaks": WORKSPACE / "outbreak_extractions_lassa" / "lassa.parquet",
}

STRATA = {
    "A_parameter_gold": {
        "description": "Full-text include with parameter gold",
        "target": 10,
    },
    "B_include_no_parameter_gold": {
        "description": "Full-text include without parameter gold",
        "target": 2,
    },
    "C_fulltext_exclude": {
        "description": "Abstract include and full-text exclude",
        "target": 8,
    },
}


def normalise_covidence(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip().str.removeprefix("#")
    return pd.to_numeric(values, errors="coerce").astype("Int64")


def stable_score(namespace: str, covidence_id: int) -> str:
    value = f"{SEED}|{namespace}|{covidence_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def safe_integer(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(int(float(value)))


def safe_text(value: object) -> str:
    return "" if pd.isna(value) else str(value).strip()


def grouped_count(frame: pd.DataFrame) -> dict[int, int]:
    ids = normalise_covidence(frame["covidence_id"])
    return ids.dropna().astype(int).value_counts().to_dict()


def grouped_parameter_classes(frame: pd.DataFrame) -> dict[int, str]:
    working = frame.assign(covidence_id_normalised=normalise_covidence(frame["covidence_id"]))
    result: dict[int, str] = {}
    for covidence_id, group in working.dropna(subset=["covidence_id_normalised"]).groupby(
        "covidence_id_normalised"
    ):
        classes = sorted({safe_text(value) for value in group["parameter_class"] if safe_text(value)})
        result[int(covidence_id)] = "; ".join(classes)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    if not audit.get("all_checks_passed"):
        raise RuntimeError("Dataset audit has not passed; sampling stopped.")
    if audit.get("revision") != "01843a781bbd839c434c50271a7b1456a59cd656":
        raise RuntimeError("Dataset revision does not match the sampling protocol.")

    screening = pd.read_parquet(SOURCE_FILES["screening"]).copy()
    parameters = pd.read_parquet(SOURCE_FILES["parameters"])
    models = pd.read_parquet(SOURCE_FILES["models"])
    outbreaks = pd.read_parquet(SOURCE_FILES["outbreaks"])

    screening["covidence_id_normalised"] = normalise_covidence(screening["covidence_id"])
    if screening["covidence_id_normalised"].isna().any():
        raise ValueError("Screening data contain missing or invalid Covidence IDs.")
    if screening["covidence_id_normalised"].duplicated().any():
        raise ValueError("Screening data contain duplicate Covidence IDs.")

    parameter_counts = grouped_count(parameters)
    model_counts = grouped_count(models)
    outbreak_counts = grouped_count(outbreaks)
    parameter_classes = grouped_parameter_classes(parameters)
    parameter_ids = set(parameter_counts)

    fulltext_include = screening["perg_fulltext_result"].eq("INCLUDE")
    abstract_include = screening["perg_abstract_result"].eq("INCLUDE")
    fulltext_exclude = screening["perg_fulltext_result"].eq("EXCLUDE")
    has_parameter_gold = screening["covidence_id_normalised"].isin(parameter_ids)

    pools = {
        "A_parameter_gold": screening[fulltext_include & has_parameter_gold].copy(),
        "B_include_no_parameter_gold": screening[fulltext_include & ~has_parameter_gold].copy(),
        "C_fulltext_exclude": screening[abstract_include & fulltext_exclude].copy(),
    }
    expected_pool_sizes = {
        "A_parameter_gold": 42,
        "B_include_no_parameter_gold": 7,
        "C_fulltext_exclude": 59,
    }
    actual_pool_sizes = {name: len(pool) for name, pool in pools.items()}
    if actual_pool_sizes != expected_pool_sizes:
        raise RuntimeError(
            f"Candidate pools changed: expected {expected_pool_sizes}, observed {actual_pool_sizes}."
        )

    selected_parts: list[pd.DataFrame] = []
    for stratum, spec in STRATA.items():
        pool = pools[stratum].copy()
        pool["selection_hash"] = pool["covidence_id_normalised"].map(
            lambda value: stable_score(stratum, int(value))
        )
        pool = pool.sort_values(["selection_hash", "covidence_id_normalised"], kind="mergesort")
        chosen = pool.head(spec["target"]).copy()
        chosen["stratum_code"] = stratum
        chosen["stratum_description"] = spec["description"]
        chosen["selection_rank_within_stratum"] = range(1, len(chosen) + 1)
        selected_parts.append(chosen)

    selected = pd.concat(selected_parts, ignore_index=True)
    selected["run_order_hash"] = selected["covidence_id_normalised"].map(
        lambda value: stable_score("run_order", int(value))
    )
    selected = selected.sort_values(["run_order_hash", "covidence_id_normalised"], kind="mergesort")
    selected = selected.reset_index(drop=True)
    selected["sample_order"] = range(1, len(selected) + 1)
    selected["sample_id"] = selected["sample_order"].map(lambda value: f"LASSA-{value:03d}")

    rows: list[dict[str, object]] = []
    for row in selected.itertuples(index=False):
        covidence_id = int(row.covidence_id_normalised)
        doi = safe_text(row.doi)
        pmcid = safe_text(row.pmcid)
        parameter_count = int(parameter_counts.get(covidence_id, 0))
        model_count = int(model_counts.get(covidence_id, 0))
        outbreak_count = int(outbreak_counts.get(covidence_id, 0))
        rows.append(
            {
                "sample_order": int(row.sample_order),
                "sample_id": row.sample_id,
                "stratum_code": row.stratum_code,
                "stratum_description": row.stratum_description,
                "selection_seed": SEED,
                "selection_rank_within_stratum": int(row.selection_rank_within_stratum),
                "selection_hash": row.selection_hash,
                "run_order_hash": row.run_order_hash,
                "covidence_id": covidence_id,
                "article_id": safe_text(row.article_id),
                "title": safe_text(row.title),
                "year": safe_integer(row.year),
                "journal": safe_text(row.journal),
                "authors": safe_text(row.authors),
                "doi": doi,
                "doi_url": f"https://doi.org/{doi}" if doi else "",
                "pmid": safe_integer(row.pmid),
                "pmcid": pmcid,
                "pmc_url": f"https://pmc.ncbi.nlm.nih.gov/articles/{pmcid}/" if pmcid else "",
                "article_url": safe_text(row.url),
                "openalex_id": safe_text(row.openalex_id),
                "metadata_source": safe_text(row.source),
                "original_download_source": safe_text(row.download_source),
                "abstract_screening_gold": safe_text(row.perg_abstract_result),
                "fulltext_screening_gold": safe_text(row.perg_fulltext_result),
                "parameter_gold_records": parameter_count,
                "parameter_classes": parameter_classes.get(covidence_id, ""),
                "model_gold_records": model_count,
                "outbreak_gold_records": outbreak_count,
                "any_extraction_gold": parameter_count + model_count + outbreak_count > 0,
            }
        )

    manifest = pd.DataFrame(rows)
    if len(manifest) != 20 or manifest["covidence_id"].duplicated().any():
        raise RuntimeError("Sample must contain 20 unique papers.")
    observed_strata = manifest["stratum_code"].value_counts().to_dict()
    expected_strata = {name: spec["target"] for name, spec in STRATA.items()}
    if observed_strata != expected_strata:
        raise RuntimeError(f"Stratum allocation mismatch: {observed_strata}.")
    if manifest["doi"].eq("").any():
        raise RuntimeError("Every selected paper must have a DOI for stable retrieval.")
    if not manifest.loc[
        manifest["stratum_code"].eq("A_parameter_gold"), "parameter_gold_records"
    ].gt(0).all():
        raise RuntimeError("Stratum A contains a paper without parameter gold.")
    if not manifest.loc[
        manifest["stratum_code"].ne("A_parameter_gold"), "parameter_gold_records"
    ].eq(0).all():
        raise RuntimeError("A non-A stratum contains parameter gold.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(args.output, index=False, lineterminator="\n")
    print(f"Wrote {len(manifest)} unique papers to {args.output}")
    print("Strata:", observed_strata)
    print("All DOI present:", not manifest["doi"].eq("").any())
    print("Papers with any extraction gold:", int(manifest["any_extraction_gold"].sum()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
