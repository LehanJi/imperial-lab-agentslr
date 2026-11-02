# Lassa dataset version record

Recorded on: 2026-10-24 (Europe/London)

## Hugging Face source

- Dataset: `OxRML/AgentSLR`
- Repository type: dataset
- Pinned revision: `01843a781bbd839c434c50271a7b1456a59cd656`
- Revision last modified: `2026-05-07T04:45:23Z`
- Dataset card SHA-256: `0a9f29cf55c7525653316c1c428bfe725ef9ed03191050c3b2cd999e8d6443bc`

## Downloaded Lassa source files

| Data | Rows | Columns | SHA-256 |
|---|---:|---:|---|
| Screening and harvest metadata | 667 | 25 | `6eaaed96c1f5167e654e74e7a9035e69c24b6659c51019a321f2a5e4d178228d` |
| Parameter extractions | 440 | 62 | `0c77cee7649609bc9138c228f533e5289b0469e8976712f16c76eb4a1ddae71d` |
| Transmission model extractions | 52 | 12 | `9d379482c5de45a87caea5f17e0d1329903475f68fe3923d63b7dd8fc2577bb3` |
| Outbreak extractions | 30 | 22 | `37e45e0977862160c3e5f05c2262c1a702c9670583c226e2f15e4f7ed10031d4` |

## Isolated AgentSLR pilot workspace

The pinned Parquet files were converted locally with:

```bash
.venv/bin/python scripts/data/download_hf_dataset.py \
  --hf-local-dir pilot/workspace/hf/AgentSLR \
  --pathogen lassa \
  --output-root pilot/workspace
```

This produced 667 harvest/screening rows, 440 parameter records, 52 model
records, and 30 outbreak records. As designed by the conversion script,
`downloaded` was reset to `False` and local PDF paths were cleared so PDF
retrieval can be reproduced on this machine. The pilot workspace is deliberately
separate from the repository's tracked `data/` directory: the released Hugging
Face screening table is a 667-row open-access subset, whereas the repository
ships a broader 2,817-row PERG screening table.

## Integrity audit

All 27 checks in `lassa_dataset_audit.json` passed. These checks cover source
and converted row counts, required screening labels, complete and unique
screening IDs, unique extraction-record IDs, conversion resets, extraction
links to the open-access screening subset, and sample-pool capacity.

Screening uses IDs such as `#2589`, while extraction tables store the same
identifier as integer `2589`. The audit normalises both forms before joins.

The open-access screening subset contains:

- 42 full-text-included papers with parameter gold records
- 7 full-text-included papers without parameter gold records
- 59 abstract-included but full-text-excluded papers

These pools are sufficient for the planned 20-paper stratified pilot. Some
gold extraction records belong to papers outside the released open-access
screening subset; the audit reports them separately and does not treat them as
downloadable pilot candidates.
