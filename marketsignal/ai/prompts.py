"""Prompt construction for the AI narrator.

The prompt hands the model a JSON payload derived entirely from the
deterministic ScoreResult (and, if available, the what-changed diff) and
asks it to synthesize that into a reasoned thesis. It is explicitly told
not to recompute scores, not to invent metrics, and not to issue a direct
Buy/Hold/Sell recommendation -- MarketSignal's design choice is an
analytical signal plus reasoning, not a directive.
"""

from __future__ import annotations

import json

from marketsignal.models import ScoreResult, WhatChanged

SYSTEM_PROMPT = (
    "You are an investment research analyst writing for someone doing their own "
    "research, not a broker giving trade instructions. You are given the "
    "deterministic output of a financial signal-scoring engine: an overall "
    "score, five category scores (Valuation, Growth, Profitability, Financial "
    "Health, Momentum), and the underlying metric values, each scored 0-4 "
    "(Weak to Strong) against fixed, transparent thresholds. "
    "Write a reasoned thesis synthesizing this data. Do not recompute or "
    "second-guess the scores, and do not invent metrics that are not in the "
    "input. Do not issue a Buy, Hold, or Sell recommendation; describe what "
    "the data shows and let the reader draw their own conclusion."
)


def build_payload(result: ScoreResult, what_changed: WhatChanged | None) -> dict:
    f = result.financials
    payload = {
        "ticker": f.ticker,
        "company_name": f.company_name,
        "sector": f.sector,
        "industry": f.industry,
        "overall_score": result.overall_score,
        "tier": result.tier,
        "categories": [
            {
                "name": c.name,
                "score": c.score,
                "metrics": [
                    {"label": m.label, "value": m.value, "score": m.score}
                    for m in c.metric_scores
                ],
            }
            for c in result.category_scores
        ],
    }
    if what_changed:
        payload["what_changed_since"] = {
            "previous_as_of": what_changed.previous_as_of,
            "overall_score_delta": what_changed.overall_score_delta,
            "category_deltas": what_changed.category_deltas,
        }
    return payload


def build_user_prompt(result: ScoreResult, what_changed: WhatChanged | None) -> str:
    payload = build_payload(result, what_changed)
    return (
        "Here is the scored research data, as JSON:\n\n"
        f"{json.dumps(payload, indent=2)}\n\n"
        "Write:\n"
        "1. A reasoned thesis (about 150-200 words) synthesizing the category "
        "scores into a coherent picture of where this company stands, in plain "
        "language.\n"
        "2. A confidence level (Low, Medium, or High) reflecting how much the "
        "signals agree with each other and how complete the underlying data is, "
        "not a market-timing call.\n"
        "3. 2-4 key risk factors grounded in the weakest signals in the data."
    )
