"""Deterministic side-by-side comparison of two already-scored tickers.

Pure transformation over two ScoreResult objects -- no network, no AI, no
new scoring model. Every research run already produces the same five
categories in the same order regardless of the ticker (score_financials()
always builds all five, with score=None for a category with no available
data rather than omitting it), so pairing them up is a straight zip, not
a lookup by id.

Only says which score is numerically bigger, in each category and
overall -- "leader" here means a higher signal score, never a
recommendation to buy the leader or sell the other one.
"""

from __future__ import annotations

from dataclasses import dataclass

from marketsignal.models import ScoreResult


def _leader(score_a: float | None, score_b: float | None) -> str | None:
    """"a" or "b" for whichever score is strictly higher; None for a tie
    or when neither side has a score to compare."""
    if score_a is None and score_b is None:
        return None
    if score_a is None:
        return "b"
    if score_b is None:
        return "a"
    if score_a > score_b:
        return "a"
    if score_b > score_a:
        return "b"
    return None


@dataclass(frozen=True)
class CategoryComparison:
    category_id: str
    category_name: str
    score_a: float | None
    score_b: float | None
    leader: str | None  # "a" / "b" / None


@dataclass(frozen=True)
class TickerComparison:
    ticker_a: str
    ticker_b: str
    company_name_a: str
    company_name_b: str
    overall_score_a: float | None
    overall_score_b: float | None
    tier_a: str
    tier_b: str
    overall_leader: str | None
    categories: tuple[CategoryComparison, ...]


def build_comparison(result_a: ScoreResult, result_b: ScoreResult) -> TickerComparison:
    categories = tuple(
        CategoryComparison(
            category_id=cat_a.id,
            category_name=cat_a.name,
            score_a=cat_a.score,
            score_b=cat_b.score,
            leader=_leader(cat_a.score, cat_b.score),
        )
        for cat_a, cat_b in zip(result_a.category_scores, result_b.category_scores)
    )

    return TickerComparison(
        ticker_a=result_a.financials.ticker,
        ticker_b=result_b.financials.ticker,
        company_name_a=result_a.financials.company_name,
        company_name_b=result_b.financials.company_name,
        overall_score_a=result_a.overall_score,
        overall_score_b=result_b.overall_score,
        tier_a=result_a.tier,
        tier_b=result_b.tier,
        overall_leader=_leader(result_a.overall_score, result_b.overall_score),
        categories=categories,
    )
