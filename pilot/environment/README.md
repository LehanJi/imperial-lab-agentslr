# Pilot environment

From the AgentSLR repository root, activate the environment with:

```bash
source .venv/bin/activate
export MPLCONFIGDIR="$PWD/.cache/matplotlib"
export PIP_CACHE_DIR="$PWD/.cache/pip"
mkdir -p "$MPLCONFIGDIR" "$PIP_CACHE_DIR"
```

Recreate the tested base environment with:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r pilot/environment/requirements-lock.txt
```

`requirements-macos-openrouter.txt` documents the direct upstream dependencies
used for this Mac/OpenRouter route. `requirements-lock.txt` records the exact
resolved environment installed and checked on 2026-10-24.

The separate OCR environment is deliberately deferred until the OCR step so
that Paddle runtime compatibility can be tested independently of this base
environment.
