"""Calls the Claude API to synthesize a ScoreResult into a structured
investment thesis: a bull case, a bear case, confidence, catalysts, risk
factors, and what would change the reader's mind. If a prior thesis
exists, the same call also checks its invalidation conditions and its
catalyst/risk-factor claims against the current data.

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

CLAIM_TYPES = ["Fact", "Inference", "Opinion"]

OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "bull_case": {"type": "string"},
        "bear_case": {"type": "string"},
        "confidence": {"type": "string", "enum": ["Low", "Medium", "High"]},
        "key_evidence": {
            "type": "array",
            "items": {"type": "string"},
        },
        "catalysts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "catalyst": {"type": "string"},
                    "claim_type": {"type": "string", "enum": CLAIM_TYPES},
                    "based_on": {"type": "string"},
                },
                "required": ["catalyst", "claim_type", "based_on"],
                "additionalProperties": False,
            },
        },
        "risk_factors": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "factor": {"type": "string"},
                    "claim_type": {"type": "string", "enum": CLAIM_TYPES},
                    "based_on": {"type": "string"},
                },
                "required": ["factor", "claim_type", "based_on"],
                "additionalProperties": False,
            },
        },
        "what_would_change_my_mind": {
            "type": "array",
            "items": {"type": "string"},
        },
        "invalidation_check": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "condition": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["Triggered", "Not triggered", "Unclear"],
                    },
                    "explanation": {"type": "string"},
                },
                "required": ["condition", "status", "explanation"],
                "additionalProperties": False,
            },
        },
        "claim_accuracy_check": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["Held up", "Did not hold up", "Too early to tell"],
                    },
                    "explanation": {"type": "string"},
                },
                "required": ["claim", "status", "explanation"],
                "additionalProperties": False,
            },
        },
    },
    "required": [
        "bull_case",
        "bear_case",
        "confidence",
        "key_evidence",
        "catalysts",
        "risk_factors",
        "what_would_change_my_mind",
        "invalidation_check",
        "claim_accuracy_check",
    ],
    "additionalProperties": False,
}


def generate_narrative(
    result: ScoreResult,
    what_changed: WhatChanged | None = None,
    previous_invalidation_conditions: list[str] | None = None,
    previous_claims: list[dict] | None = None,
) -> dict:
    load_dotenv()
    client = anthropic.Anthropic()

    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": build_user_prompt(
                    result, what_changed, previous_invalidation_conditions, previous_claims
                ),
            }
        ],
        output_config={"format": {"type": "json_schema", "schema": OUTPUT_SCHEMA}},
    )

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
