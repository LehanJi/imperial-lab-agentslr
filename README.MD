# AgentSLR Evaluation Harness

<table style="border-collapse: separate; border-spacing: 20px 0;">
  <tr>
    <td align="center" style="padding: 4px 8px;">
      <a href="https://arxiv.org/abs/2603.22327">
        <img src="assets/icons/arxiv.svg" alt="Paper" width="15" valign="middle"> <strong>Paper</strong>
      </a>
    </td>
    <td align="center" style="padding: 4px 8px;">
      <a href="https://huggingface.co/datasets/OxRML/AgentSLR">
        <img src="assets/icons/hf.svg" alt="Dataset" width="15" valign="middle"> <strong>Dataset</strong>
      </a>
    </td>
    <td align="center" style="padding: 4px 8px;">
      <a href="https://oxrml.com/agent-slr/">
        <img src="assets/icons/website.svg" alt="Project Website" width="15" valign="middle"> <strong>Project Website</strong>
      </a>
    </td>
  </tr>
</table>

AgentSLR is the open-source evaluation harness used in the paper **Evaluating AI-based Scientific Knowledge Synthesis with Epidemiological Systematic Reviews**. It contains the LLM-assisted systematic literature review workflow and the scripts needed to use the accompanying Hugging Face dataset.

The harness is built to download article metadata and labels, retrieve available full-text PDFs, run abstract screening, OCR, full-text screening, extraction and write-up stages, then evaluate generated artefacts against PERG ground truth.

<p align="center">
  <img src="assets/figures/pipeline_flashfig.jpeg" alt="AgentSLR pipeline overview" width="100%">
</p>
<p align="center">
  <em>AgentSLR runs the review flow from search and retrieval to screening, extraction and report generation.</em>
</p>

## Contents

- [AgentSLR Harness](#agentslr-harness)
- [Repository Overview](#repository-overview)
- [Data Workspace](#data-workspace)
- [Environment Setup](#environment-setup)
- [Downloading The Dataset](#downloading-the-dataset)
- [Running AgentSLR (LLM-assisted SLRs)](#running-agentslr-workflow-llm-assisted-slrs)
- [Running With OpenRouter Or Local vLLM](#running-with-openrouter-or-local-vllm)
- [Evaluation Protocols And Scripts](#evaluation-protocols-and-scripts)
- [Citation](#citation)

## Repository Overview

| Directory | Purpose | Documentation |
|-----------|---------|---------------|
| [`src/harvest/`](src/harvest/) | Metadata retrieval and PDF download | [README](src/harvest/README.md) |
| [`src/screening/`](src/screening/) | Abstract and full-text screening | [README](src/screening/README.md) |
| [`src/ocr/`](src/ocr/) | PDF-to-Markdown conversion | [README](src/ocr/README.md) |
| [`src/extraction/`](src/extraction/) | Structured data extraction | [README](src/extraction/README.md) |
| [`src/analysis/`](src/analysis/) | Report generation | [README](src/analysis/README.md) |
| [`scripts/`](scripts/) | Shell wrappers and data utilities | See subdirectory READMEs |
| [`eval/`](eval/) | Evaluation against PERG ground truth | [README](eval/README.md) |
| [`notebooks/`](notebooks/) | Paper figures and statistics | [README](notebooks/README.md) |

[`main.py`](main.py) is the single CLI entrypoint for the workflow. It supports the WHO priority pathogen review topics used in the harness: Marburg, Ebola, Lassa, SARS, Zika, MERS, Nipah, Rift Valley fever and Crimean-Congo haemorrhagic fever.

## Data Workspace

The harness keeps harvest artefacts separate from model-specific outputs. Assuming `data/agentslr` is the main output directory, the local workspace looks like this:

```text
data/
├── agentslr/
│   ├── harvests/
│   │   └── <pathogen>/
│   │       ├── harvest_metadata.csv
│   │       ├── harvest_downloaded_pdfs.csv
│   │       ├── articles_with_markdown.csv
│   │       ├── pdfs/
│   │       └── ocr/
│   │           └── <ocr_client>/
│   │               └── markdown/
│   └── client/
│       └── <client_dir_name>/
│           └── <pathogen>/
│               ├── screening/
│               │   ├── abstract_screening.csv
│               │   └── fulltext_screening.csv
│               ├── extractions/
│               │   ├── data_extraction_parameters.jsonl
│               │   ├── data_extraction_models.csv
│               │   └── data_extraction_outbreaks.csv
│               ├── report/
│               └── logs/
└── perg/
    ├── screening/
    └── extracted/
```

`client_dir_name` is either inferred from `--model-name` or set explicitly with `--client-dir-name`. Use a stable name when comparing models, prompts or OCR settings.

## Environment Setup

### Base Environment

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

Use this environment for harvest, screening, extraction, evaluation and report generation. It also works for the Mistral OCR API.

### OCR Environment

If you want local OCR backends such as GLM or Paddle, create a dedicated OCR environment:

```bash
python3 -m venv .venv-ocr
source .venv-ocr/bin/activate
pip install --upgrade pip

# Install a torch build that matches your machine first
pip install torch

# Install exactly one Paddle runtime
pip install paddlepaddle

pip install -r requirements-ocr.txt
```

For GPU Paddle, install the matching `paddlepaddle-gpu` package instead.

### API Keys And Config

You can pass credentials on the command line or store them in `config.json`:

```json
{
  "openai_api_key": "your-openai-api-key",
  "openrouter_api_key": "your-openrouter-api-key",
  "mistral_api_key": "your-mistral-api-key"
}
```

Useful environment variables:

```bash
export OPENAI_API_KEY="..."
export OPENALEX_API_KEY="..."
export NCBI_API_KEY="..."
export NCBI_EMAIL="you@example.com"
export UNPAYWALL_EMAIL="you@example.com"
export MISTRAL_API_KEY="..."
```

## Downloading The Dataset

The Hugging Face dataset contains article metadata, screening labels and extraction labels. It does not redistribute the article PDFs. Download the dataset files first, convert them into the harness layout, then run the PDF download stage.

Download the Hugging Face files for a single pathogen:

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="OxRML/AgentSLR",
    repo_type="dataset",
    local_dir="data/hf/AgentSLR",
    allow_patterns=[
        "data/harvest_metadata_and_screening/lassa.parquet",
        "data/parameter_extractions_lassa/lassa.parquet",
        "data/transmission_model_extractions_lassa/lassa.parquet",
        "data/outbreak_extractions_lassa/lassa.parquet",
    ],
)
PY
```

For the complete dataset, omit `allow_patterns`:

```bash
python - <<'PY'
from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="OxRML/AgentSLR",
    repo_type="dataset",
    local_dir="data/hf/AgentSLR",
)
PY
```

Convert the downloaded Hugging Face files into the local harness layout:

```bash
python scripts/data/download_hf_dataset.py \
  --hf-local-dir data/hf/AgentSLR \
  --pathogen lassa \
  --output-root data
```

If you do not need to keep a separate Hugging Face download, the same helper can fetch and convert directly:

```bash
python scripts/data/download_hf_dataset.py \
  --pathogen lassa \
  --output-root data
```

For Lassa, this writes:

```text
data/agentslr/harvests/lassa/harvest_metadata.csv
data/perg/screening/Lassa_filtered.csv
data/perg/extracted/lassa_parameters.csv
data/perg/extracted/lassa_models.csv
data/perg/extracted/lassa_outbreaks.csv
```

The conversion step resets `downloaded` to `False` and clears local PDF paths. That makes PDF retrieval reproducible on a new machine.

Download available PDFs from the converted metadata:

```bash
python main.py \
  --stage harvest \
  --pathogen lassa \
  --harvest-mode download_only \
  --data-dir data/agentslr \
  --metadata-input data/agentslr/harvests/lassa/harvest_metadata.csv \
  --article-downloading-workers 4 \
  --progress-every 25 \
  --log-level INFO
```

The output is written to:

```text
data/agentslr/harvests/lassa/harvest_downloaded_pdfs.csv
data/agentslr/harvests/lassa/pdfs/
```

For a quick smoke test, use a small metadata subset and keep `--article-downloading-workers` low.

## Running AgentSLR (LLM-assisted SLRs)

You can run the full pipeline or run individual stages. Individual stages are easier to inspect and are recommended when testing a new model or provider.

### Quickstart

```bash
python main.py \
  --stage run_all \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name <model-name> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json \
  --ocr-client mistral
```

To resume a full run from a later stage:

```bash
python main.py \
  --stage run_all \
  --resume-from fulltext_screen \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name <model-name> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json
```

### Detailed Usage Arguments

The key `main.py` arguments for workflow runs are:

| Argument | Required? | What to pass | Why it matters |
| --- | --- | --- | --- |
| `--stage` | Yes | A stage from the table below, often `run_all`. | Selects which pipeline block to run. |
| `--pathogen` | Yes | One of `marburg`, `ebola`, `lassa`, `sars`, `zika`, `nipah`, `rvf`, `cchf`, `mers`. | Chooses the review topic and query set. |
| `--data-dir` | Optional | A workspace root such as `data/agentslr`. | Controls where harvests, screening outputs, extractions and reports are written. |
| `--model-name` | Recommended | A provider model identifier. The paper evaluates `gpt-oss-120b`, `GPT-5.2`, `DeepSeek-V3.2`, `Kimi-K2.5` and `GLM-4.7`. | Determines the model used for screening, extraction and default report stages. |
| `--client-dir-name` | Recommended | A stable short label such as `gpt_oss_120b`. | Keeps outputs for different models or settings separated. |
| `--base-url` | Optional | An OpenAI-compatible endpoint, such as OpenAI, OpenRouter or local vLLM. | Routes requests to the selected provider. |
| `--api-key` | Optional | Matching API key. Local vLLM commonly uses `6767`. | Authenticates requests to the configured endpoint. |
| `--config-json` | Optional | Usually `config.json`. | Loads saved API keys such as OpenAI, OpenRouter or Mistral credentials. |
| `--resume-from` | Optional | A later stage such as `ocr`, `fulltext_screen` or `write_up_parameters`. | Used with `--stage run_all` to continue from that stage. |
| `--ocr-client` | Optional | `mistral`, `glm` or `paddle`. | Selects the OCR backend. |
| `--fulltext-input-mode` | Optional | `markdown` or `pdf`. | Uses OCR Markdown or direct PDF input for full-text stages. |
| `--skip-ocr` | Optional | Flag only. | Skips OCR in `run_all` and passes PDFs directly to supported multimodal models. |
| `--reasoning` | Optional | Enabled by default. | Sends reasoning parameters to supported models. |
| `--no-reasoning` | Optional | Flag only. | Removes reasoning parameters for non-reasoning models or gateways. |
| `--max-completion-tokens` | Optional | Token budget, often `65536` for paper-style runs. | Prevents truncated structured outputs. |
| `--report-model-name` | Optional | A report model identifier. | Lets write-up refinement use a different model. |

### Reasoning And Non-reasoning Models

Reasoning parameters are enabled by default. Disable them for models or gateways that do not accept reasoning fields:

```bash
--no-reasoning
```

Use `--reasoning-effort low|medium|high` for models that support it. Use `--no-report-reasoning` if the report refinement model should not receive reasoning parameters.

### OCR Route

This is the most portable route. PDFs are converted to Markdown first, then the LLM reads the Markdown.

```bash
python main.py \
  --stage ocr \
  --pathogen lassa \
  --data-dir data/agentslr \
  --ocr-input-source harvest_downloaded_pdfs \
  --ocr-client mistral \
  --ocr-workers 1 \
  --config-json config.json \
  --log-level INFO
```

Run full-text screening on the OCR output:

```bash
python main.py \
  --stage fulltext_screen \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name <model-name> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json \
  --fulltext-screening-mode direct_fulltext \
  --fulltext-screening-batch-size 1 \
  --fulltext-screening-concurrency 1 \
  --max-completion-tokens 65536
```

Then run extraction on the generated full-text decisions:

```bash
python main.py \
  --stage data_extraction_outbreaks \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name <model-name> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json \
  --limit 1 \
  --data-extraction-concurrency 1 \
  --max-completion-tokens 65536
```

The same pattern applies to `data_extraction_parameters` and `data_extraction_models`.

### Direct PDF Route Without OCR

For multimodal models that accept PDF file inputs, skip OCR and pass downloaded PDFs directly to the model.

Run only full-text screening from downloaded PDFs:

```bash
python main.py \
  --stage fulltext_screen \
  --pathogen lassa \
  --data-dir data/agentslr \
  --screening-input data/agentslr/harvests/lassa/harvest_downloaded_pdfs.csv \
  --fulltext-input-mode pdf \
  --model-name <multimodal-model> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json \
  --fulltext-screening-batch-size 1 \
  --fulltext-screening-concurrency 1 \
  --max-completion-tokens 65536
```

Use `--skip-ocr` with `run_all` to omit OCR in an end-to-end run:

```bash
python main.py \
  --stage run_all \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name <multimodal-model> \
  --client-dir-name <client-dir-name> \
  --base-url <api-endpoint> \
  --config-json config.json \
  --skip-ocr \
  --fulltext-screening-mode direct_fulltext
```

Provider support varies. Direct PDF input requires a multimodal model and an endpoint that accepts PDF file parts. If downstream extraction uses tools, verify that the same model supports tool calls with PDF inputs. Inline PDF payloads are redacted from local trace JSON. Test a small sample before scaling a direct-PDF run. Add `--no-reasoning` when using a non-reasoning model.

### Stage Reference

| Stage | What it does | Typical use |
| --- | --- | --- |
| `harvest` | Fetches metadata, deduplicates results and downloads PDFs. | Start a new corpus or download PDFs from HF metadata. |
| `run_all` | Runs harvest, abstract screening, OCR or direct PDF full-text screening, extraction and write-up. | Standard end-to-end run. |
| `abstract_screen` | Screens titles and abstracts. | Re-run abstract inclusion or exclusion. |
| `ocr` | Converts PDFs into Markdown using `mistral`, `glm` or `paddle`. | Prepare article text for full-text screening and extraction. |
| `fulltext_screen` | Screens OCR Markdown or attached PDFs. | Re-run full-text decisions after model or prompt changes. |
| `data_extraction_parameters` | Extracts epidemiological parameter data. | Parameter-focused extraction runs. |
| `data_extraction_models` | Extracts transmission and modelling-study information. | Model-study extraction runs. |
| `data_extraction_outbreaks` | Extracts outbreak-event information. | Outbreak-focused extraction runs. |
| `write_up_parameters` | Generates the parameter report. | Parameter report generation. |
| `write_up_models` | Generates the modelling report. | Model report generation. |
| `write_up_outbreaks` | Generates the outbreak report. | Outbreak report generation. |

## Running With OpenRouter Or Local vLLM

The screening, extraction and report stages use an OpenAI-compatible client interface. You can point AgentSLR at OpenAI, OpenRouter or a local vLLM server with `--base-url`, `--api-key` and `--model-name`.

### OpenRouter

```bash
python main.py \
  --stage fulltext_screen \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name openai/gpt-oss-120b \
  --client-dir-name gpt_oss_120b \
  --base-url https://openrouter.ai/api/v1 \
  --config-json config.json \
  --fulltext-screening-mode direct_fulltext \
  --max-completion-tokens 65536
```

OpenRouter keys can be loaded from `config.json` as `openrouter_api_key`.

### Local vLLM

Serve a local model:

```bash
scripts/serve_vllm/serve_client.sh
```

The helper defaults to port `6767`, API key `6767`, model `openai/gpt-oss-20b`, GPU IDs `0`, tensor parallel size `1`, `--max-model-len 131072`, and `--async-scheduling`. You can override them with optional args such as `--port`, `--api-key`, `--model-name`, `--gpu-ids`, `--tp-size`, and repeated `--extra-vllm-arg`.

You can also run the equivalent command directly:

```bash
vllm serve openai/gpt-oss-120b \
  --port 6767 \
  --api-key 6767 \
  --tensor-parallel-size 2 \
  --max-model-len 131072 \
  --async-scheduling
```

Then point AgentSLR at it:

```bash
python main.py \
  --stage run_all \
  --pathogen lassa \
  --data-dir data/agentslr \
  --model-name openai/gpt-oss-120b \
  --client-dir-name gpt_oss_120b \
  --base-url http://localhost:6767/v1 \
  --api-key 6767
```

Additional serving notes for DeepSeek, Kimi and GLM are in [`scripts/serve_vllm/README.md`](scripts/serve_vllm/README.md).

## Evaluation Protocols And Scripts

Evaluation reads the generated harness artefacts and compares them against PERG labels. Use the output root that contains both `agentslr/` and `perg/` as `--data-dir`.

Abstract screening:

```bash
python -m eval.run_eval abstract_screening \
  --pathogen Lassa \
  --screened data/agentslr/client/<client_dir_name>/lassa/screening/abstract_screening.csv \
  --data-dir data \
  --output-dir data/agentslr/evals \
  --identifier <run_name>
```

Full-text screening:

```bash
python -m eval.run_eval fulltext_screening \
  --pathogen Lassa \
  --fulltext-screened data/agentslr/client/<client_dir_name>/lassa/screening/fulltext_screening.csv \
  --abstract-screened data/agentslr/client/<client_dir_name>/lassa/screening/abstract_screening.csv \
  --data-dir data \
  --output-dir data/agentslr/evals \
  --identifier <run_name> \
  --mode all
```

Outbreak extraction:

```bash
python -m eval.run_eval outbreak_extraction \
  --pathogen Lassa \
  --extracted data/agentslr/client/<client_dir_name>/lassa/extractions/data_extraction_outbreaks.csv \
  --fulltext-screening data/agentslr/client/<client_dir_name>/lassa/screening/fulltext_screening.csv \
  --data-dir data \
  --output-dir data/agentslr/evals \
  --identifier <run_name>
```

Model and parameter extraction follow the same pattern:

```bash
python -m eval.run_eval model_extraction \
  --pathogen Lassa \
  --extracted data/agentslr/client/<client_dir_name>/lassa/extractions/data_extraction_models.csv \
  --fulltext-screening data/agentslr/client/<client_dir_name>/lassa/screening/fulltext_screening.csv \
  --data-dir data \
  --output-dir data/agentslr/evals \
  --identifier <run_name>

python -m eval.run_eval parameter_extraction \
  --pathogen Lassa \
  --extracted data/agentslr/client/<client_dir_name>/lassa/extractions/data_extraction_parameters.jsonl \
  --fulltext-screening data/agentslr/client/<client_dir_name>/lassa/screening/fulltext_screening.csv \
  --data-dir data \
  --output-dir data/agentslr/evals \
  --identifier <run_name>
```

See [`eval/README.md`](eval/README.md) for full evaluation documentation.

## Citation

If you use AgentSLR, please cite:

```bibtex
@misc{padarha2025agentslr,
  title={AgentSLR: Automating Systematic Literature Reviews
         in Epidemiology with Agentic AI},
  author={Padarha, Shreyansh and Kearns, Ryan Othniel
          and Naidoo, Tristan and Yang, Lingyi
          and Borchmann, {\L}ukasz and B{\l}aszczyk, Piotr
          and Morgenstern, Christian and McCabe, Ruth
          and Bhatia, Sangeeta and Torr, Philip H.
          and Foerster, Jakob and Hale, Scott A.
          and Rawson, Thomas and Cori, Anne
          and Semenova, Elizaveta and Mahdi, Adam},
  year={2026},
  eprint={2603.22327},
  archivePrefix={arXiv},
  primaryClass={cs.IR},
  url={https://arxiv.org/abs/2603.22327}
}
```
