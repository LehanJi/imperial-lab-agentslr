# Step 4 — Free full-text PDF retrieval and validation

Completed: 2026-10-24

## Outcome

- Target records: **20**
- PDFs obtained: **20/20**
- Automated integrity and identity checks passed: **20/20**
- Total pages: **273** (range: 5–29 pages)
- Total size: **27,989,291 bytes**
- Paid APIs or subscriptions used: **none**
- Re-running AgentSLR in `download_only` mode reports 20 already downloaded and 0 to process.

The sample retained the predeclared strata:

| Stratum | Description | PDFs | Passed |
|---|---|---:|---:|
| A | Parameter-positive gold set | 10 | 10 |
| B | Included by review, no parameter gold label | 2 | 2 |
| C | Full-text exclusion controls | 8 | 8 |

## Retrieval sources

| Source | Count | Cost |
|---|---:|---|
| Unpaywall | 8 | Free |
| PMC Open Access cloud PDFs | 5 | Free |
| Europe PMC full text | 5 | Free |
| OpenAlex/CDC Stacks PDF URL | 1 | Free |
| PMC article rendered to PDF in Safari | 1 | Free |

The browser-rendered fallback is `LASSA-011` (PMID 25404077, PMCID PMC4347375). The direct PMC PDF endpoint returned HTTP 403 to unattended clients, while the public PMC article page exposed the complete article. Safari's print-to-PDF produced a 20-page, text-searchable PDF containing the full article, tables, DOI, PMID and PMCID. This fallback is explicitly labelled `PMC_browser_print_to_PDF` in the download manifest rather than being presented as the publisher-formatted file.

## Corrections and compatibility work

The pinned PERG/Hugging Face dataset contained seven stale or incorrect PMCID values. They were preserved in `source_pmcid`, replaced only after DOI/PMID/title verification, and accompanied by an evidence URL:

- LASSA-001 → PMC4995818
- LASSA-007 → PMC10823436
- LASSA-009 → PMC5468694
- LASSA-010 → PMC7984835
- LASSA-011 → PMC4347375
- LASSA-013 → PMC10031424
- LASSA-016 → PMC8637796

The AgentSLR harvester also required two compatibility fixes:

1. The NCBI identifier converter was updated to the current PMC endpoint.
2. The retired PMC OA package API was replaced with the official public PMC Open Access S3 bucket workflow.

The original values and evidence URLs remain in the download CSV for provenance. The code fixes are covered by two regression tests.

## Validation protocol

`pilot/scripts/audit_pilot_pdfs.py` performs the same checks for every sample row:

1. Confirm the declared file exists and begins with `%PDF`.
2. Parse the PDF with Poppler and require at least one page.
3. Require a non-trivial file size (at least 10,000 bytes).
4. Extract text with Poppler and require at least 500 characters.
5. Normalize the target title and calculate title-token coverage in the extracted full text.
6. Normalize the target DOI and look for it in the extracted text.
7. Pass identity when the DOI is present or title-token coverage is at least 0.70.
8. Record source, page count, size, SHA-256, text length and evidence in the audit CSV.

All 20 files passed with **1.000 title-token coverage**, and all 20 contained the expected DOI. First-page renderings from each PDF were also produced; representative files from all retrieval routes were visually inspected and showed legible, correctly matched articles.

## Reproduction commands

Run from the repository root with the existing `.venv`:

```bash
.venv/bin/python main.py --stage harvest --pathogen lassa \
  --data-dir pilot/workspace/agentslr \
  --harvest-mode download_only \
  --metadata-input pilot/workspace/agentslr/harvests/lassa/pilot_sample_downloads.csv \
  --harvest-metadata-filename pilot_sample_metadata.csv \
  --harvest-downloaded-pdfs-filename pilot_sample_downloads.csv \
  --harvest-progress-filename pilot_sample_download_progress.csv \
  --pdf-dirname pilot_pdfs \
  --article-downloading-workers 2 \
  --progress-every 1 \
  --ncbi-email literature-review@example.org \
  --unpaywall-email literature-review@example.org

.venv/bin/python pilot/scripts/audit_pilot_pdfs.py
.venv/bin/python -m unittest discover -s pilot/tests -v
```

## Outputs

- PDF directory: `pilot/workspace/agentslr/harvests/lassa/pilot_pdfs/`
- Download/provenance manifest: `pilot/workspace/agentslr/harvests/lassa/pilot_sample_downloads.csv`
- Per-PDF audit: `pilot/data/lassa_pdf_retrieval_audit.csv`
- Audit script: `pilot/scripts/audit_pilot_pdfs.py`
- PMCID correction script: `pilot/scripts/apply_verified_pmcid_corrections.py`

Audit CSV SHA-256:

```text
495324b689b88eb39d82bca3002650401d9f07a1d0f53c13cc01a2489b41d40b
```

## External references

- PMC Open Access cloud documentation: https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/
- PMC ID Converter API: https://pmc.ncbi.nlm.nih.gov/tools/id-converter-api/
- LASSA-007 CDC Stacks source: https://stacks.cdc.gov/view/cdc/147658
- LASSA-011 PMC article: https://pmc.ncbi.nlm.nih.gov/articles/PMC4347375/
