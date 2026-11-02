# Step 5 — Free local full-text extraction

Completed: 2026-10-24

## Outcome

- Input PDFs: **20**
- Markdown files created: **20/20**
- Automated validation passed: **20/20**
- Pages preserved: **273/273**
- Extracted text: **1,463,638 characters** and **101,627 normalized words**
- Quantitative tokens detected: **18,941**
- Explicit table references detected: **141**
- API cost: **£0 / $0**
- Re-run result: **20 skipped, 0 errors**, confirming idempotence

Every Markdown file contains the expected title and DOI, has the same page count as its source PDF, and exceeds the minimum text-length threshold.

## Method decision

AgentSLR originally offers Mistral OCR, GLM-OCR and PaddleOCR-VL. Mistral requires an API key; GLM and Paddle require a separate model environment and substantially more compute. The 20 pilot PDFs are born-digital and already contain usable text layers, so running vision OCR on every page would add cost and transcription risk without improving basic text recovery.

A `poppler` backend was added to AgentSLR for this pilot. It runs `pdftotext -layout`, writes one Markdown file per article, inserts explicit page markers, and populates the normal `articles_with_markdown.csv` output used by later AgentSLR stages. Image-only PDFs fail clearly and instruct the operator to use GLM, Paddle or Mistral OCR.

This is a free text-extraction baseline, not image OCR. It retains approximate spacing and page boundaries but does not reconstruct embedded figures or semantic HTML table structure. The extraction audit therefore records numeric-token and table-reference coverage, while the later parameter-extraction validation must check source-page provenance for every reported value.

## Validation criteria

Each article passes only when all of the following are true:

1. AgentSLR reports `success` or `skipped`.
2. The Markdown file exists.
3. It contains at least 5,000 characters.
4. Markdown page markers, extracted page count and source PDF page count match.
5. Normalized title-token coverage is at least 70%.
6. The expected DOI occurs in the extracted text.

All 20 articles achieved 100% title-token coverage and contained their expected DOI.

## Reproduction command

```bash
.venv/bin/python main.py \
  --stage ocr \
  --pathogen lassa \
  --data-dir pilot/workspace/agentslr \
  --ocr-client poppler \
  --ocr-input-source harvest_downloaded_pdfs \
  --ocr-input pilot/workspace/agentslr/harvests/lassa/pilot_sample_downloads.csv \
  --ocr-workers 4 \
  --poppler-pdftotext-bin /path/to/pdftotext

.venv/bin/python pilot/scripts/audit_markdown_extraction.py
```

## Outputs

- Markdown files: `pilot/workspace/agentslr/harvests/lassa/ocr/poppler/markdown/`
- Combined AgentSLR input: `pilot/workspace/agentslr/harvests/lassa/articles_with_markdown.csv`
- Machine-readable audit: `pilot/data/lassa_markdown_extraction_audit.json`
- Reader-facing audit workbook: `/Users/jilehan/Desktop/urop/lassa_markdown_extraction_audit.xlsx`

The next stage is quantitative-parameter extraction on the ten `A_parameter_gold` papers, followed by comparison with the PERG gold-standard labels.
