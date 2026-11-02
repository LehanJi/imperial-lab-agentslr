# Lassa pilot full-text screening smoke test

Recorded on: 2026-10-24 (Europe/London)

## Configuration

- Stage: `fulltext_screen`
- Input: `articles_with_markdown_blinded.csv`
- Rows sent: 1 of 20, sampled with seed `20261024`
- Model: `nvidia/nemotron-3-ultra-550b-a55b:free`
- Provider: OpenRouter
- Full-text input mode: Markdown
- Gold-label columns were removed before inference.

## Result

- Article: `PMID_33657095`
- Title: *Bridging the gap: Using reservoir ecology and human serosurveys to estimate Lassa virus spillover in West Africa*
- Model decision: `INCLUDE`
- PERG gold decision, revealed only after inference: `INCLUDE`
- Agreement: yes
- Prompt tokens: 26,690
- Completion tokens: 1,143
- Total tokens: 27,833
- Reported cost: `$0`
- Wall-clock model run: approximately 19 seconds

## Output

The AgentSLR-compatible result is stored at:

`pilot/workspace/agentslr/client/nemotron3_ultra_free/lassa/screening/fulltext_screening.csv`

The reasoning trace is stored beneath the matching timestamped directory in:

`pilot/workspace/agentslr/client/nemotron3_ultra_free/lassa/logs/`

This smoke test confirms that the free OpenRouter model can ingest the pilot's
full Markdown article, return a parseable AgentSLR decision, and preserve the
blinded comparison workflow before scaling to all 20 papers.
