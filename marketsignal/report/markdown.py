"""Renders a ScoreResult (plus optional what-changed diff and AI thesis) as
a Markdown research brief."""

from __future__ import annotations

from marketsignal.comparison import TickerComparison
from marketsignal.models import ScoreResult, WhatChanged
from marketsignal.scoring import SIGNAL_LEVELS, tier_for_score
from marketsignal.sector_benchmarks import build_valuation_sector_view

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

        if category.id == "valuation":
            sector_comparisons = build_valuation_sector_view(f)
            if sector_comparisons:
                lines.append(f"**vs. {f.sector} sector median:**")
                lines.append("")
                for c in sector_comparisons:
                    lines.append(
                        f"- {c.metric_label}: {c.ticker_value:.2f} vs. {c.sector_median:.2f} "
                        f"-- {c.label}"
                    )
                lines.append("")

    if ai_narrative:
        lines.append("## Thesis")
        lines.append("")
        lines.append(f"**Confidence:** {ai_narrative.get('confidence', 'n/a')}")
        lines.append("")
        lines.append("### Bull case")
        lines.append("")
        lines.append(ai_narrative.get("bull_case", "").strip())
        lines.append("")
        lines.append("### Bear case")
        lines.append("")
        lines.append(ai_narrative.get("bear_case", "").strip())
        lines.append("")

        evidence = ai_narrative.get("key_evidence", [])
        if evidence:
            lines.append(f"**Key evidence:** {', '.join(evidence)}")
            lines.append("")

        catalysts = ai_narrative.get("catalysts", [])
        if catalysts:
            lines.append("### Catalysts to watch")
            lines.append("")
            for catalyst in catalysts:
                lines.append(
                    f"- {catalyst['catalyst']} "
                    f"[{catalyst['claim_type']}, based on {catalyst['based_on']}]"
                )
            lines.append("")

        risks = ai_narrative.get("risk_factors", [])
        if risks:
            lines.append("### Key risk factors")
            lines.append("")
            for risk in risks:
                lines.append(
                    f"- {risk['factor']} [{risk['claim_type']}, based on {risk['based_on']}]"
                )
            lines.append("")

        change_mind = ai_narrative.get("what_would_change_my_mind", [])
        if change_mind:
            lines.append("### What would change this view")
            lines.append("")
            for item in change_mind:
                lines.append(f"- {item}")
            lines.append("")

        invalidation_check = ai_narrative.get("invalidation_check", [])
        if invalidation_check:
            lines.append("### Invalidation check (conditions from the last thesis)")
            lines.append("")
            for check in invalidation_check:
                lines.append(
                    f"- **{check['status']}** -- {check['condition']} "
                    f"({check['explanation']})"
                )
            lines.append("")

        claim_accuracy_check = ai_narrative.get("claim_accuracy_check", [])
        if claim_accuracy_check:
            lines.append("### Claim accuracy check (claims from the last thesis)")
            lines.append("")
            for check in claim_accuracy_check:
                lines.append(
                    f"- **{check['status']}** -- {check['claim']} ({check['explanation']})"
                )
            lines.append("")

    return "\n".join(lines)


def _score_cell(score: float | None) -> str:
    if score is None:
        return "n/a"
    return f"{score:.2f} ({tier_for_score(score)})"


def render_comparison(comparison: TickerComparison) -> str:
    c = comparison
    lines: list[str] = []

    lines.append(f"# Comparing {c.ticker_a} vs. {c.ticker_b}")
    lines.append("")
    lines.append(f"| | {c.ticker_a} ({c.company_name_a}) | {c.ticker_b} ({c.company_name_b}) |")
    lines.append("|---|---|---|")
    overall_leader = c.ticker_a if c.overall_leader == "a" else (
        c.ticker_b if c.overall_leader == "b" else "Tie"
    )
    lines.append(
        f"| Overall | {_score_cell(c.overall_score_a)} | {_score_cell(c.overall_score_b)} |"
    )
    lines.append("")
    lines.append(f"**Overall leader:** {overall_leader}")
    lines.append("")

    lines.append("## By category")
    lines.append("")
    lines.append(f"| Category | {c.ticker_a} | {c.ticker_b} | Leader |")
    lines.append("|---|---|---|---|")
    for cat in c.categories:
        leader = c.ticker_a if cat.leader == "a" else (c.ticker_b if cat.leader == "b" else "Tie")
        lines.append(
            f"| {cat.category_name} | {_score_cell(cat.score_a)} | "
            f"{_score_cell(cat.score_b)} | {leader} |"
        )
    lines.append("")
    lines.append(
        '"Leader" means a higher deterministic signal score, category by category -- '
        "not a recommendation to buy the leader or sell the other one. See each "
        "ticker's own full research report for metric-level detail."
    )

    return "\n".join(lines)
