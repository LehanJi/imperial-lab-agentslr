# AgentSLR pilot version record

Recorded on: 2026-10-24 (Europe/London)

## Source code

- Repository: https://github.com/OxRML/AgentSLR
- Branch at retrieval: `main`
- Pinned commit: `3111fcf456c6fbcba768dfdce2bd2934d8cb5cef`
- Commit timestamp: `2026-05-07T15:10:45Z`
- Commit URL: https://github.com/OxRML/AgentSLR/commit/3111fcf456c6fbcba768dfdce2bd2934d8cb5cef
- Commit-specific ZIP SHA-256: `e8a6e49c149aec7e7c8097b48495440dcdbdefa7c5b45d19ad4de909f5195b2c`
- Verification: the downloaded `main` archive was compared recursively with
  the commit-specific archive and no file differences were found.

## Local environment

- Host OS: macOS 14.4, arm64
- Environment directory: `.venv`
- Python: `3.12.14`
- Initial pip: `25.0.1`
- Planned inference route: OpenRouter OpenAI-compatible API
- Local `vllm`: intentionally excluded because this Mac pilot does not serve
  the model on an NVIDIA GPU.

## Reproducibility settings

- Pilot pathogen: Lassa fever
- Sampling seed: `20261024`
- Target sample size: `20` articles

The dataset revision is recorded in `../data/DATASET_VERSION.md`. The selected
model endpoint will be recorded before its first use in a later step. The final
installed base-package lock is recorded in `requirements-lock.txt`.
