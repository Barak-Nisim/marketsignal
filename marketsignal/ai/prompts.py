"""Prompt construction for the AI narrator.

The prompt hands the model a JSON payload derived entirely from the
deterministic ScoreResult (and, if available, the what-changed diff) and
asks it to synthesize that into a structured investment thesis: a bull
case, a bear case, catalysts, risk factors, and what would change the
reader's mind. It is explicitly told not to recompute scores, not to
invent metrics, and not to issue a direct Buy/Hold/Sell recommendation --
MarketSignal's design choice is an analytical signal plus reasoning, not
a directive.
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
    "Write a structured bull case and bear case grounded in this data. Do not "
    "recompute or second-guess the scores, and do not invent metrics that are "
    "not in the input. Do not issue a Buy, Hold, or Sell recommendation; "
    "describe what the data shows on both sides and let the reader draw their "
    "own conclusion. The bear case should be genuinely argued, not a token "
    "counterpoint -- if the data supports real concerns, say so plainly. "
    "For every catalyst and risk factor, classify it as one of three claim "
    "types so the reader can judge how much weight to give it: 'Fact' (a "
    "value directly present in the input data, not interpreted), 'Inference' "
    "(a reasoned conclusion drawn from one or more input values, e.g. what a "
    "combination of metrics implies), or 'Opinion' (your own judgment about "
    "materiality or likelihood that goes beyond what the data alone shows). "
    "Do not over-classify as Fact -- if it required any reasoning to state, "
    "it is an Inference or Opinion, not a Fact."
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
        "1. A 'bull_case' (about 80-120 words): the strongest case for this "
        "being a good investment right now, grounded in the data.\n"
        "2. A 'bear_case' (about 80-120 words): the strongest case against it, "
        "equally grounded in the data. Do not soften this to be agreeable.\n"
        "3. A confidence level (Low, Medium, or High) reflecting how much the "
        "signals agree with each other and how complete the underlying data is, "
        "not a market-timing call.\n"
        "4. 2-4 'key_evidence' entries: the category or metric names (exactly as "
        "given in the input, e.g. 'Valuation' or 'Financial Health: Debt to "
        "Equity') that most heavily inform both cases. Every conclusion should "
        "be traceable back to specific data, not general impressions.\n"
        "5. 2-4 'catalysts', each an object with 'catalyst' (a specific, "
        "concrete event or data point that could meaningfully move this "
        "signal in the near future, e.g. an upcoming earnings report or a "
        "metric approaching a threshold -- grounded in what's actually "
        "knowable from the data, not speculation about unannounced events), "
        "'claim_type' (Fact, Inference, or Opinion, as defined above), and "
        "'based_on' (the specific category or metric name, exactly as given "
        "in the input, that grounds it).\n"
        "6. 2-4 key risk factors, each an object with 'factor' (the risk "
        "itself), 'claim_type' (Fact, Inference, or Opinion, as defined "
        "above), and 'based_on' (the specific category or metric name, "
        "exactly as given in the input, that grounds it). Do not write a "
        "risk factor that isn't traceable to a specific signal in the data.\n"
        "7. 2-3 'what_would_change_my_mind' entries: specific, falsifiable "
        "conditions that would flip this view (e.g. 'if revenue growth turns "
        "negative next quarter'), not vague hedges."
    )
