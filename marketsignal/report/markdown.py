"""Renders a ScoreResult (plus optional what-changed diff and AI thesis) as
a Markdown research brief."""

from __future__ import annotations

from marketsignal.models import ScoreResult, WhatChanged
from marketsignal.scoring import SIGNAL_LEVELS, tier_for_score

PERCENT_METRICS = {
    "revenue_growth",
    "earnings_growth",
    "gross_margin",
    "operating_margin",
    "return_on_equity",
    "price_change_3mo",
    "price_change_12mo",
    "pct_of_52wk_range",
}


def format_value(key: str, value: float | None) -> str:
    if value is None:
        return "n/a"
    if key in PERCENT_METRICS:
        return f"{value * 100:.1f}%"
    return f"{value:.2f}"


def _format_delta(delta: float | None) -> str:
    if delta is None:
        return "n/a"
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.2f}"


def render(
    result: ScoreResult,
    what_changed: WhatChanged | None = None,
    ai_narrative: dict | None = None,
) -> str:
    lines: list[str] = []
    f = result.financials

    lines.append(f"# MarketSignal Research Brief: {f.company_name} ({f.ticker})")
    lines.append("")
    lines.append(f"**Sector:** {f.sector or 'n/a'} / {f.industry or 'n/a'}  ")
    lines.append(f"**As of:** {f.as_of}  ")
    if result.overall_score is not None:
        lines.append(f"**Overall Signal:** {result.overall_score:.2f} / 4.0 ({result.tier})")
    else:
        lines.append("**Overall Signal:** insufficient data")
    lines.append("")

    if what_changed:
        lines.append(f"## What changed since {what_changed.previous_as_of}")
        lines.append("")
        lines.append(f"Overall signal: {_format_delta(what_changed.overall_score_delta)}")
        for category_id, delta in what_changed.category_deltas.items():
            lines.append(f"- {category_id.replace('_', ' ').title()}: {_format_delta(delta)}")
        lines.append("")

    lines.append("## Category Scores")
    lines.append("")
    lines.append("| Category | Score | Signal |")
    lines.append("|---|---|---|")
    for category in result.category_scores:
        if category.score is not None:
            lines.append(
                f"| {category.name} | {category.score:.2f} | {tier_for_score(category.score)} |"
            )
        else:
            lines.append(f"| {category.name} | n/a | No data available |")
    lines.append("")

    lines.append("## Metric Detail")
    lines.append("")
    for category in result.category_scores:
        lines.append(f"### {category.name}")
        lines.append("")
        lines.append("| Metric | Value | Signal |")
        lines.append("|---|---|---|")
        for metric in category.metric_scores:
            value_str = format_value(metric.key, metric.value)
            signal_str = SIGNAL_LEVELS[metric.score] if metric.score is not None else "n/a"
            lines.append(f"| {metric.label} | {value_str} | {signal_str} |")
        lines.append("")

    if ai_narrative:
        lines.append("## Thesis")
        lines.append("")
        lines.append(f"**Confidence:** {ai_narrative.get('confidence', 'n/a')}")
        lines.append("")
        lines.append(ai_narrative.get("thesis", "").strip())
        lines.append("")

        risks = ai_narrative.get("risk_factors", [])
        if risks:
            lines.append("### Key risk factors")
            lines.append("")
            for risk in risks:
                lines.append(f"- {risk}")
            lines.append("")

    return "\n".join(lines)
