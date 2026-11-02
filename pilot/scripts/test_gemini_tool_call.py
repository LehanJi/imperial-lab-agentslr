#!/usr/bin/env python3
"""Minimal Gemini/OpenAI compatibility test without displaying the API key."""

from __future__ import annotations

import json
from pathlib import Path

from openai import OpenAI


def main() -> int:
    config = json.loads(Path("config.json").read_text(encoding="utf-8"))
    client = OpenAI(
        api_key=config["gemini_api_key"],
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        timeout=30.0,
        max_retries=0,
    )
    tool = {
        "type": "function",
        "function": {
            "name": "record_measurement",
            "description": "Record the requested numeric measurement.",
            "parameters": {
                "type": "object",
                "properties": {
                    "value": {"type": "number"},
                    "unit": {"type": "string"},
                },
                "required": ["value", "unit"],
            },
        },
    }
    response = client.chat.completions.create(
        model="gemini-3.5-flash-lite",
        messages=[
            {
                "role": "user",
                "content": (
                    "Use record_measurement to record exactly 7.7e-4 "
                    "substitutions/site/year."
                ),
            }
        ],
        tools=[tool],
        tool_choice="required",
        max_completion_tokens=256,
    )
    calls = response.choices[0].message.tool_calls or []
    if not calls:
        raise RuntimeError("Gemini returned no tool call")
    args = json.loads(calls[0].function.arguments)
    print(
        json.dumps(
            {"tool": calls[0].function.name, "arguments": args},
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
