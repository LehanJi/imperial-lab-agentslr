#!/usr/bin/env python3
"""Save a Gemini API key from the macOS clipboard without printing it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    key = subprocess.run(
        ["pbpaste"], check=True, capture_output=True, text=True
    ).stdout.strip()
    if not key.startswith(("AIza", "AQ.")) or len(key) < 35:
        raise ValueError("Clipboard does not contain a valid Gemini API key")

    config: dict[str, object] = {}
    if args.output.exists():
        config = json.loads(args.output.read_text(encoding="utf-8"))
    config["gemini_api_key"] = key

    args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(
        f"Saved Gemini key to {args.output} with mode 0600 "
        "(value not displayed)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
