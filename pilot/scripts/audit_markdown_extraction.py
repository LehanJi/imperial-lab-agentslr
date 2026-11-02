#!/usr/bin/env python3
"""Create a reproducible JSON audit of the pilot's extracted Markdown."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "pilot/workspace/agentslr/harvests/lassa/articles_with_markdown.csv"
PDF_AUDIT = ROOT / "pilot/data/lassa_pdf_retrieval_audit.csv"
OUTPUT = ROOT / "pilot/data/lassa_markdown_extraction_audit.json"

STOPWORDS = {
    "a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of",
    "on", "or", "the", "to", "with", "using", "among", "study", "analysis",
}
QUANTITATIVE_PATTERNS = {
    "reproduction_number": r"\b(?:basic\s+)?reproduction\s+(?:number|ratio)|\bR\s*0\b",
    "incubation_period": r"\bincubation\s+period\b",
    "case_fatality": r"\bcase[- ]fatality|\bfatality\s+(?:rate|ratio)\b",
    "mortality": r"\bmortality\b",
    "seroprevalence": r"\bseroprevalence\b|\bsero[- ]?prevalence\b",
    "confidence_interval": r"\bconfidence\s+interval\b|\b95\s*%\s*CI\b",
    "odds_ratio": r"\bodds\s+ratio\b|\bA?OR\b",
    "relative_risk": r"\brelative\s+risk\b|\brisk\s+ratio\b",
    "transmission": r"\btransmission\b|\btransmissibility\b",
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
    return re.sub(r"^doi:\s*", "", doi).rstrip(".,;)")


def main() -> None:
    data = pd.read_csv(INPUT).sort_values("sample_order")
    pdf_audit = pd.read_csv(PDF_AUDIT).set_index("sample_id")
    records = []
    for _, row in data.iterrows():
        sample_id = str(row["sample_id"])
        markdown_path = Path(str(row.get("markdown_path", "")))
        markdown = (
            markdown_path.read_text(encoding="utf-8", errors="ignore")
            if markdown_path.is_file()
            else ""
        )
        title_tokens = sorted(set(normalized_words(row.get("title", ""))))
        body_words = normalized_words(markdown)
        body_set = set(body_words)
        found = sum(token in body_set for token in title_tokens)
        title_coverage = found / len(title_tokens) if title_tokens else 0.0
        doi = normalize_doi(row.get("doi", ""))
        doi_present = bool(doi and doi in re.sub(r"\s+", "", markdown.lower()))
        pdf_pages = int(pdf_audit.loc[sample_id, "page_count"])
        extracted_pages = int(row.get("ocr_num_pages", 0) or 0)
        page_markers = len(re.findall(r"<!-- PAGE \d+ -->", markdown))
        quant_hits = {
            name: len(re.findall(pattern, markdown, flags=re.IGNORECASE))
            for name, pattern in QUANTITATIVE_PATTERNS.items()
        }
        numeric_tokens = len(
            re.findall(r"(?<![A-Za-z])[-+]?\d+(?:[.,]\d+)*(?:\s*%)?", markdown)
        )
        table_mentions = len(
            re.findall(r"\b(?:table|supplementary table)\s+[A-Z]?\d+", markdown, re.IGNORECASE)
        )
        sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest() if markdown else ""

        checks = {
            "ocr_success": str(row.get("ocr_status", "")).lower() in {"success", "skipped"},
            "file_exists": markdown_path.is_file(),
            "text_length": len(markdown) >= 5_000,
            "page_count": extracted_pages == pdf_pages == page_markers,
            "title_identity": title_coverage >= 0.70,
            "doi_identity": doi_present,
        }
        passed = all(checks.values())
        failed_checks = [name for name, ok in checks.items() if not ok]
        records.append(
            {
                "sample_id": sample_id,
                "sample_order": int(row["sample_order"]),
                "stratum_code": str(row.get("stratum_code", "")),
                "title": str(row.get("title", "")),
                "doi": doi,
                "download_source": str(row.get("download_source", "")),
                "markdown_file": markdown_path.name,
                "ocr_client": str(row.get("ocr_client", "")),
                "ocr_model_name": str(row.get("ocr_model_name", "")),
                "pdf_pages": pdf_pages,
                "extracted_pages": extracted_pages,
                "page_markers": page_markers,
                "markdown_chars": len(markdown),
                "word_count": len(body_words),
                "numeric_token_count": numeric_tokens,
                "numeric_tokens_per_1000_words": round(
                    numeric_tokens * 1000 / max(1, len(body_words)), 1
                ),
                "table_mentions": table_mentions,
                "quantitative_term_hits": sum(quant_hits.values()),
                "quantitative_term_breakdown": quant_hits,
                "title_token_coverage": round(title_coverage, 3),
                "doi_present": doi_present,
                "sha256": sha256,
                "validation_status": "PASS" if passed else "REVIEW",
                "validation_note": (
                    "identity, completeness and text thresholds verified"
                    if passed
                    else "failed checks: " + ", ".join(failed_checks)
                ),
            }
        )

    summary = {
        "records": len(records),
        "passed": sum(record["validation_status"] == "PASS" for record in records),
        "review": sum(record["validation_status"] != "PASS" for record in records),
        "total_pages": sum(record["extracted_pages"] for record in records),
        "total_markdown_chars": sum(record["markdown_chars"] for record in records),
        "total_words": sum(record["word_count"] for record in records),
        "total_numeric_tokens": sum(record["numeric_token_count"] for record in records),
        "total_table_mentions": sum(record["table_mentions"] for record in records),
        "method": "Poppler pdftotext -layout; page boundaries retained as Markdown comments",
        "limitation": (
            "This is born-digital text extraction, not image OCR. Approximate spacing is retained, "
            "but embedded figures and semantic HTML table structure are not reconstructed."
        ),
    }
    payload = {"summary": summary, "records": records}
    OUTPUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"Audit JSON: {OUTPUT}")
    if summary["review"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
