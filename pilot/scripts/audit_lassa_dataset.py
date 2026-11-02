#!/usr/bin/env python3
"""Audit the pinned Lassa AgentSLR source and converted data files."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
PILOT_WORKSPACE = ROOT / "pilot" / "workspace"
HF_ROOT = PILOT_WORKSPACE / "hf" / "AgentSLR" / "data"

SOURCE_FILES = {
    "screening": HF_ROOT / "harvest_metadata_and_screening" / "lassa.parquet",
    "parameters": HF_ROOT / "parameter_extractions_lassa" / "lassa.parquet",
    "models": HF_ROOT / "transmission_model_extractions_lassa" / "lassa.parquet",
    "outbreaks": HF_ROOT / "outbreak_extractions_lassa" / "lassa.parquet",
}

CONVERTED_FILES = {
    "harvest": PILOT_WORKSPACE / "agentslr" / "harvests" / "lassa" / "harvest_metadata.csv",
    "screening": PILOT_WORKSPACE / "perg" / "screening" / "Lassa_filtered.csv",
    "parameters": PILOT_WORKSPACE / "perg" / "extracted" / "lassa_parameters.csv",
    "models": PILOT_WORKSPACE / "perg" / "extracted" / "lassa_models.csv",
    "outbreaks": PILOT_WORKSPACE / "perg" / "extracted" / "lassa_outbreaks.csv",
}

EXPECTED_ROWS = {
    "screening": 667,
    "parameters": 440,
    "models": 52,
    "outbreaks": 30,
}

RECORD_ID_COLUMNS = {
    "parameters": "parameter_data_id",
    "models": "model_data_id",
    "outbreaks": "outbreak_data_id",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalise_covidence(series: pd.Series) -> pd.Series:
    values = series.astype("string").str.strip().str.removeprefix("#")
    return pd.to_numeric(values, errors="coerce").astype("Int64")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    source = {name: pd.read_parquet(path) for name, path in SOURCE_FILES.items()}
    converted = {name: pd.read_csv(path) for name, path in CONVERTED_FILES.items()}

    checks: list[dict[str, object]] = []

    def check(name: str, passed: bool, detail: object) -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    for name, expected in EXPECTED_ROWS.items():
        actual = len(source[name])
        check(f"source_{name}_row_count", actual == expected, {"expected": expected, "actual": actual})

    screening = source["screening"].copy()
    screening["covidence_id_normalised"] = normalise_covidence(screening["covidence_id"])
    check(
        "screening_covidence_id_complete",
        screening["covidence_id_normalised"].notna().all(),
        int(screening["covidence_id_normalised"].isna().sum()),
    )
    check(
        "screening_covidence_id_unique",
        not screening["covidence_id_normalised"].duplicated().any(),
        int(screening["covidence_id_normalised"].duplicated().sum()),
    )
    check("screening_downloaded_all_true", screening["downloaded"].eq(True).all(), int(screening["downloaded"].sum()))
    check("screening_perg_subset_all_true", screening["perg_subset"].eq(True).all(), int(screening["perg_subset"].sum()))

    allowed_labels = {"INCLUDE", "EXCLUDE"}
    for field in ("perg_abstract_result", "perg_fulltext_result"):
        observed = set(screening[field].dropna().unique())
        check(f"{field}_valid", observed <= allowed_labels and not screening[field].isna().any(), sorted(observed))

    harvest = converted["harvest"].copy()
    check("converted_harvest_row_count", len(harvest) == len(screening), len(harvest))
    check("converted_screening_row_count", len(converted["screening"]) == len(screening), len(converted["screening"]))
    check("converted_downloaded_reset_false", harvest["downloaded"].eq(False).all(), int(harvest["downloaded"].sum()))
    check("converted_download_path_cleared", harvest["downloaded_path"].isna().all(), int(harvest["downloaded_path"].notna().sum()))

    screening_ids = set(screening["covidence_id_normalised"].dropna().astype(int))
    extraction_summary: dict[str, object] = {}

    for name in ("parameters", "models", "outbreaks"):
        frame = source[name]
        ids = normalise_covidence(frame["covidence_id"])
        unique_ids = set(ids.dropna().astype(int))
        matched_ids = unique_ids & screening_ids
        record_id_column = RECORD_ID_COLUMNS[name]
        check(f"{name}_covidence_id_complete", ids.notna().all(), int(ids.isna().sum()))
        check(f"{name}_record_id_complete", frame[record_id_column].notna().all(), int(frame[record_id_column].isna().sum()))
        check(f"{name}_record_id_unique", not frame[record_id_column].duplicated().any(), int(frame[record_id_column].duplicated().sum()))
        check(f"converted_{name}_row_count", len(converted[name]) == len(frame), len(converted[name]))
        extraction_summary[name] = {
            "records": len(frame),
            "unique_papers_all_gold": len(unique_ids),
            "unique_papers_in_oa_screening_subset": len(matched_ids),
            "unique_papers_outside_oa_screening_subset": len(unique_ids - screening_ids),
        }

    parameter_ids = set(normalise_covidence(source["parameters"]["covidence_id"]).dropna().astype(int))
    fulltext_include = screening["perg_fulltext_result"].eq("INCLUDE")
    abstract_include = screening["perg_abstract_result"].eq("INCLUDE")
    fulltext_exclude = screening["perg_fulltext_result"].eq("EXCLUDE")
    has_parameter = screening["covidence_id_normalised"].isin(parameter_ids)

    candidate_pools = {
        "fulltext_include_with_parameter_gold": int((fulltext_include & has_parameter).sum()),
        "fulltext_include_without_parameter_gold": int((fulltext_include & ~has_parameter).sum()),
        "abstract_include_fulltext_exclude": int((abstract_include & fulltext_exclude).sum()),
    }
    ready_for_sampling = (
        candidate_pools["fulltext_include_with_parameter_gold"] >= 10
        and candidate_pools["fulltext_include_without_parameter_gold"] >= 2
        and candidate_pools["abstract_include_fulltext_exclude"] >= 8
    )
    check("candidate_pools_support_planned_20_article_sample", ready_for_sampling, candidate_pools)

    report = {
        "dataset": "OxRML/AgentSLR",
        "revision": "01843a781bbd839c434c50271a7b1456a59cd656",
        "source_files": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
                "rows": len(source[name]),
                "columns": len(source[name].columns),
            }
            for name, path in SOURCE_FILES.items()
        },
        "screening_labels": {
            "abstract": screening["perg_abstract_result"].value_counts(dropna=False).to_dict(),
            "fulltext": screening["perg_fulltext_result"].value_counts(dropna=False).to_dict(),
        },
        "extractions": extraction_summary,
        "parameter_classes": source["parameters"]["parameter_class"].value_counts(dropna=False).to_dict(),
        "candidate_pools": candidate_pools,
        "checks": checks,
        "all_checks_passed": all(item["passed"] for item in checks),
    }

    rendered = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if report["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
