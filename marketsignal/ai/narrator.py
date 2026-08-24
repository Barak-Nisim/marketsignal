"""Calls the Claude API to synthesize a ScoreResult into a reasoned thesis,
confidence level, and risk factors.

This module never recomputes or overrides scores -- it only narrates the
deterministic output of marketsignal.scoring. Requires ANTHROPIC_API_KEY
(see .env.example); not exercised by the test suite or CI, which run with
mocked responses.
"""

from __future__ import annotations

import json

import anthropic
from dotenv import load_dotenv

from marketsignal.ai.prompts import SYSTEM_PROMPT, build_user_prompt
from marketsignal.models import ScoreResult, WhatChanged

MODEL = "claude-opus-4-8"

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "thesis": {"type": "string"},
        "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "risk_factors": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["thesis", "confidence", "risk_factors"],
    "additionalProperties": False,
}


def generate_narrative(result: ScoreResult, what_changed: WhatChanged | None = None) -> dict:
    load_dotenv()
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_user_prompt(result, what_changed)}],
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
