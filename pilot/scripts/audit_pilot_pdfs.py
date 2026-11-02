#!/usr/bin/env python3
"""Audit every pilot PDF for integrity and target-paper identity."""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "pilot/workspace/agentslr/harvests/lassa/pilot_sample_downloads.csv"
OUTPUT = ROOT / "pilot/data/lassa_pdf_retrieval_audit.csv"
PDFINFO = Path(
    "/Users/jilehan/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/bin/override/pdfinfo"
)
PDFTOTEXT = Path(
    "/Users/jilehan/.cache/codex-runtimes/codex-primary-runtime/"
    "dependencies/native/poppler/poppler/bin/pdftotext"
)

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "using", "among", "study", "analysis",
}


def normalized_words(value: object) -> list[str]:
    text = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode()
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [word for word in words if len(word) >= 3 and word not in STOPWORDS]


def normalize_doi(value: object) -> str:
    doi = str(value).strip().lower()
    if doi in {"", "nan", "none"}:
        return ""
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi.rstrip(".,;)")


def run_checked(command: list[str]) -> str:
    result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().replace("\n", " ")
        raise RuntimeError(detail[:300] or f"exit {result.returncode}")
    return result.stdout


def parse_pdfinfo(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            parsed[key.strip()] = value.strip()
    return parsed


def audit_row(row: pd.Series) -> dict[str, object]:
    path = Path(str(row.get("downloaded_path", "")))
    record: dict[str, object] = {
        "sample_id": row.get("sample_id", ""),
        "sample_order": row.get("sample_order", ""),
        "stratum_code": row.get("stratum_code", ""),
        "title": row.get("title", ""),
        "doi": row.get("doi", ""),
        "pmid": row.get("pmid", ""),
        "pmcid": row.get("pmcid", ""),
        "download_source": row.get("download_source", ""),
        "downloaded_path": str(path),
        "exists": path.is_file(),
        "pdf_header_ok": False,
        "file_size_bytes": "",
        "sha256": "",
        "page_count": "",
        "encrypted": "",
        "pdf_version": "",
        "text_char_count": "",
        "title_token_count": "",
        "title_tokens_found": "",
        "title_token_coverage": "",
        "doi_present": False,
        "identity_evidence": "",
        "validation_status": "FAIL",
        "validation_note": "",
    }
    if not path.is_file():
        record["validation_note"] = "file missing"
        return record

    data = path.read_bytes()
    record["pdf_header_ok"] = data.startswith(b"%PDF")
    record["file_size_bytes"] = len(data)
    record["sha256"] = hashlib.sha256(data).hexdigest()
    if not record["pdf_header_ok"]:
        record["validation_note"] = "missing %PDF header"
        return record

    try:
        info = parse_pdfinfo(run_checked([str(PDFINFO), str(path)]))
        pages = int(info.get("Pages", "0"))
        record["page_count"] = pages
        record["encrypted"] = info.get("Encrypted", "")
        record["pdf_version"] = info.get("PDF version", "")
        text = run_checked([str(PDFTOTEXT), "-enc", "UTF-8", str(path), "-"])
    except Exception as exc:  # per-file diagnostic is written to the audit table
        record["validation_note"] = f"PDF parser error: {exc}"
        return record

    normalized_text = " ".join(normalized_words(text))
    title_tokens = sorted(set(normalized_words(row.get("title", ""))))
    found = [token for token in title_tokens if re.search(rf"\b{re.escape(token)}\b", normalized_text)]
    coverage = len(found) / len(title_tokens) if title_tokens else 0.0
    doi = normalize_doi(row.get("doi", ""))
    doi_compact = re.sub(r"\s+", "", text.lower())
    doi_present = bool(doi and doi in doi_compact)

    record["text_char_count"] = len(text.strip())
    record["title_token_count"] = len(title_tokens)
    record["title_tokens_found"] = len(found)
    record["title_token_coverage"] = f"{coverage:.3f}"
    record["doi_present"] = doi_present

    integrity_ok = pages > 0 and len(data) >= 10_000 and len(text.strip()) >= 500
    identity_ok = doi_present or coverage >= 0.70
    if doi_present and coverage >= 0.70:
        evidence = "DOI+title"
    elif doi_present:
        evidence = "DOI"
    elif coverage >= 0.70:
        evidence = "title"
    else:
        evidence = "insufficient"
    record["identity_evidence"] = evidence
    record["validation_status"] = "PASS" if integrity_ok and identity_ok else "FAIL"
    if record["validation_status"] == "PASS":
        record["validation_note"] = "integrity and target identity verified"
    elif not integrity_ok:
        record["validation_note"] = "integrity/text threshold not met"
    else:
        record["validation_note"] = "title/DOI identity threshold not met"
    return record


def main() -> None:
    if not PDFINFO.is_file() or not PDFTOTEXT.is_file():
        raise SystemExit("Bundled Poppler tools are unavailable")
    df = pd.read_csv(INPUT).sort_values("sample_order")
    records = [audit_row(row) for _, row in df.iterrows()]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    passed = sum(record["validation_status"] == "PASS" for record in records)
    print(f"Audited {len(records)} PDFs: {passed} PASS, {len(records) - passed} FAIL")
    for record in records:
        print(
            f"{record['sample_id']}: {record['validation_status']} "
            f"pages={record['page_count']} title={record['title_token_coverage']} "
            f"doi={record['doi_present']} source={record['download_source']}"
        )
    print(f"Audit CSV: {OUTPUT}")
    if passed != len(records):
        sys.exit(1)


if __name__ == "__main__":
    main()
