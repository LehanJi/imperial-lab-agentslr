# Lassa pilot sampling protocol

Recorded on: 2026-10-24 (Europe/London)

## Objective

Select 20 open-access Lassa fever papers for a small, reproducible AgentSLR
pilot that can test both screening and quantitative extraction against the
released PERG gold data.

## Sampling frame

The sampling frame is the 667-paper open-access Lassa subset in the pinned
`OxRML/AgentSLR` dataset revision recorded in `DATASET_VERSION.md`. Sampling
starts only after `lassa_dataset_audit.json` reports that all integrity checks
passed.

## Allocation

| Stratum | Eligibility | Papers |
|---|---|---:|
| A | Full-text INCLUDE and at least one parameter gold record | 10 |
| B | Full-text INCLUDE and no parameter gold record | 2 |
| C | Abstract INCLUDE and full-text EXCLUDE | 8 |
| Total |  | 20 |

Stratum A supports quantitative-extraction validation. Strata B and C provide
screening and false-positive controls without assuming that every included
paper contains a target parameter.

## Reproducible selection

- Seed: `20261024`
- Sampling unit: one unique normalised Covidence article ID
- Selection: rank each eligible article by SHA-256 of
  `seed|stratum|covidence_id`, then take the required number without replacement
- Run order: independently rank the 20 selected articles by SHA-256 of
  `seed|run_order|covidence_id`
- Ties: resolve by ascending normalised Covidence ID

Hash ranking is used so the same source revision produces the same sample
across Python, NumPy and pandas versions. The manifest retains both hashes and
the within-stratum rank for auditability.

## Required checks

The selection script stops if the dataset audit failed, the dataset revision or
candidate-pool sizes changed, IDs are invalid or duplicated, the allocation is
not 10/2/8, a selected paper lacks a DOI, or the parameter-gold strata do not
match their definitions.

## Generated manifest

- File: `lassa_pilot_sample.csv`
- Rows: 20 unique papers
- SHA-256: `04c5623ecf60fe265ab898c870c7c59746a0c9b516b2db201b3d6e5cd7f60ff2`
- Publication years: 2009–2023
- Original open-access retrieval sources: 19 Europe PMC Full Text, 1 Unpaywall
- Gold records represented: 30 parameter, 3 transmission-model, 3 outbreak

An independent repeat run produced a byte-identical manifest.
