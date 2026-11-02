#!/usr/bin/env python3
"""Save an OpenRouter key from the macOS clipboard without printing it."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--stdin",
        action="store_true",
        help="Read the key from one stdin line instead of the macOS clipboard",
    )
    args = parser.parse_args()

    if args.stdin:
        key = sys.stdin.readline().strip()
    else:
        key = subprocess.run(
            ["pbpaste"], check=True, capture_output=True, text=True
        ).stdout.strip()
    if not key.startswith("sk-or-v1-") or len(key) < 40:
        raise ValueError("Clipboard does not contain a valid OpenRouter API key")

    config: dict[str, object] = {}
    if args.output.exists():
        config = json.loads(args.output.read_text(encoding="utf-8"))
    config["openrouter_api_key"] = key

    args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(f"Saved OpenRouter key to {args.output} with mode 0600 (value not displayed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
