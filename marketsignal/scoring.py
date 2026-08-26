"""Pure deterministic scoring engine: RawFinancials -> ScoreResult.

No I/O, no network calls -- this is what makes the scoring fully
unit-testable and explainable independent of the AI narrator layer, exactly
like RiskLens's scoring.py.

Every metric is scored 0-4 ("Weak" to "Strong") against a fixed, documented
threshold table below -- there is no machine-learned model and no hidden
curve. A missing metric (common for ETFs, which lack income-statement data
entirely) is excluded from its category's average rather than scored as 0;
see models.py for why that differs from RiskLens's "missing = worst case"
rule. If every metric in a category is unavailable, that category is
excluded from the overall score the same way.
"""

from __future__ import annotations

from marketsignal.models import (
    SIGNAL_LEVELS,
    CategoryScore,
    MetricScore,
    RawFinancials,
    ScoreResult,
)

TIER_BOUNDARIES = (
    (0.8, "Weak"),
    (1.6, "Below Average"),
    (2.4, "Average"),
    (3.2, "Above Average"),
    (float("inf"), "Strong"),
)


def tier_for_score(score: float) -> str:
    for boundary, tier in TIER_BOUNDARIES:
        if score < boundary:
            return tier
    return "Strong"


def signal_bucket(score: float) -> str:
    """Collapses the five-tier system to three CSS color buckets (strong /
    average / weak) for compact bar-chart displays, e.g. the portfolio
    review's category-average bars."""
    tier = tier_for_score(score)
    if tier in ("Strong", "Above Average"):
        return "strong"
    if tier == "Average":
        return "average"
    return "weak"


def _band(
    value: float | None, bands: list[tuple[float, int]], *, higher_is_better: bool
) -> int | None:
    """bands is a list of (threshold, score) pairs. For higher_is_better,
    bands are checked as value >= threshold, ordered highest threshold
    first. For lower_is_better, checked as value <= threshold, ordered
    lowest threshold first."""
    if value is None:
        return None
    for threshold, score in bands:
        if higher_is_better and value >= threshold:
            return score
        if not higher_is_better and value <= threshold:
            return score
    return 0


def _positive_or_none(value: float | None) -> float | None:
    """Ratios like P/E and PEG are only meaningful when positive -- a
    negative P/E (from negative earnings) isn't "cheap," it's a different
    situation entirely, so it's excluded rather than misleadingly scored."""
    if value is not None and value > 0:
        return value
    return None


def _pct_of_52wk_range(financials: RawFinancials) -> float | None:
    low, high, price = (
        financials.fifty_two_week_low,
        financials.fifty_two_week_high,
        financials.current_price,
    )
    if low is None or high is None or price is None or high <= low:
        return None
    return (price - low) / (high - low)


def _metric(key: str, label: str, value: float | None, score: int | None) -> MetricScore:
    return MetricScore(key=key, label=label, value=value, score=score)


def _category_score(metric_scores: tuple[MetricScore, ...]) -> float | None:
    available = [m.score for m in metric_scores if m.score is not None]
    if not available:
        return None
    return sum(available) / len(available)


def score_financials(financials: RawFinancials) -> ScoreResult:
    valuation_metrics = (
        _metric(
            "trailing_pe",
            "Trailing P/E",
            financials.trailing_pe,
            _band(
                _positive_or_none(financials.trailing_pe),
                [(10, 4), (15, 3), (25, 2), (40, 1)],
                higher_is_better=False,
            ),
        ),
        _metric(
            "price_to_book",
            "Price / Book",
            financials.price_to_book,
            _band(
                financials.price_to_book, [(1, 4), (3, 3), (5, 2), (8, 1)], higher_is_better=False
            ),
        ),
        _metric(
            "price_to_sales",
            "Price / Sales",
            financials.price_to_sales,
            _band(
                financials.price_to_sales,
                [(1, 4), (3, 3), (6, 2), (10, 1)],
                higher_is_better=False,
            ),
        ),
        _metric(
            "peg_ratio",
            "PEG Ratio",
            financials.peg_ratio,
            _band(
                _positive_or_none(financials.peg_ratio),
                [(1, 4), (1.5, 3), (2, 2), (3, 1)],
                higher_is_better=False,
            ),
        ),
    )

    growth_metrics = (
        _metric(
            "revenue_growth",
            "Revenue Growth (YoY)",
            financials.revenue_growth,
            _band(
                financials.revenue_growth,
                [(0.20, 4), (0.10, 3), (0.05, 2), (0, 1)],
                higher_is_better=True,
            ),
        ),
        _metric(
            "earnings_growth",
            "Earnings Growth (YoY)",
            financials.earnings_growth,
            _band(
                financials.earnings_growth,
                [(0.20, 4), (0.10, 3), (0.05, 2), (0, 1)],
                higher_is_better=True,
            ),
        ),
    )

    profitability_metrics = (
        _metric(
            "gross_margin",
            "Gross Margin",
            financials.gross_margin,
            _band(
                financials.gross_margin,
                [(0.50, 4), (0.35, 3), (0.20, 2), (0.05, 1)],
                higher_is_better=True,
            ),
        ),
        _metric(
            "operating_margin",
            "Operating Margin",
            financials.operating_margin,
            _band(
                financials.operating_margin,
                [(0.25, 4), (0.15, 3), (0.05, 2), (0, 1)],
                higher_is_better=True,
            ),
        ),
        _metric(
            "return_on_equity",
            "Return on Equity",
            financials.return_on_equity,
            _band(
                financials.return_on_equity,
                [(0.25, 4), (0.15, 3), (0.08, 2), (0, 1)],
                higher_is_better=True,
            ),
        ),
    )

    financial_health_metrics = (
        _metric(
            "debt_to_equity",
            "Debt / Equity",
            financials.debt_to_equity,
            _band(
                financials.debt_to_equity,
                [(50, 4), (100, 3), (150, 2), (250, 1)],
                higher_is_better=False,
            ),
        ),
        _metric(
            "current_ratio",
            "Current Ratio",
            financials.current_ratio,
            _band(
                financials.current_ratio,
                [(2, 4), (1.5, 3), (1, 2), (0.75, 1)],
                higher_is_better=True,
            ),
        ),
    )

    pct_range = _pct_of_52wk_range(financials)
    momentum_metrics = (
        _metric(
            "price_change_12mo",
            "12-Month Price Change",
            financials.price_change_12mo,
            _band(
                financials.price_change_12mo,
                [(0.30, 4), (0.15, 3), (0, 2), (-0.15, 1)],
                higher_is_better=True,
            ),
        ),
        _metric(
            "price_change_3mo",
            "3-Month Price Change",
            financials.price_change_3mo,
            _band(
                financials.price_change_3mo,
                [(0.15, 4), (0.05, 3), (-0.05, 2), (-0.15, 1)],
                higher_is_better=True,
            ),
        ),
        _metric(
            "pct_of_52wk_range",
            "Position in 52-Week Range",
            pct_range,
            _band(pct_range, [(0.8, 4), (0.6, 3), (0.4, 2), (0.2, 1)], higher_is_better=True),
        ),
    )

    categories = (
        CategoryScore(
            "valuation", "Valuation", _category_score(valuation_metrics), valuation_metrics
        ),
        CategoryScore("growth", "Growth", _category_score(growth_metrics), growth_metrics),
        CategoryScore(
            "profitability",
            "Profitability",
            _category_score(profitability_metrics),
            profitability_metrics,
        ),
        CategoryScore(
            "financial_health",
            "Financial Health",
            _category_score(financial_health_metrics),
            financial_health_metrics,
        ),
        CategoryScore("momentum", "Momentum", _category_score(momentum_metrics), momentum_metrics),
    )

    available_category_scores = [c.score for c in categories if c.score is not None]
    overall_score = (
        sum(available_category_scores) / len(available_category_scores)
        if available_category_scores
        else None
    )
    tier = tier_for_score(overall_score) if overall_score is not None else "Unknown"

    return ScoreResult(
        financials=financials,
        overall_score=overall_score,
        tier=tier,
        category_scores=categories,
    )


__all__ = ["score_financials", "tier_for_score", "SIGNAL_LEVELS"]
