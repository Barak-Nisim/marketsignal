"""Aggregates a set of already-scored holdings into one portfolio-level
read.

Pure function, no I/O, no network, no AI call -- mirrors accuracy.py and
outcomes.py's pattern of a dedicated module that only does math over data
someone else already fetched. Every number here is a deterministic
average of the same five signals score_financials() already produces for
each holding; there is no new scoring model and no numeric growth
projection (see docs/enhancements.md for why that was deliberately cut).
"""

from __future__ import annotations

from marketsignal.models import PortfolioReview, ScoreResult
from marketsignal.scoring import tier_for_score


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def build_portfolio_review(
    portfolio_name: str,
    results: list[ScoreResult],
    failed_tickers: list[str],
) -> PortfolioReview:
    overall_score = _mean([r.overall_score for r in results if r.overall_score is not None])
    tier = tier_for_score(overall_score) if overall_score is not None else None

    # every ScoreResult shares the same fixed category order (see
    # scoring.py), so the first holding's order is the canonical order --
    # building from a set here would give an arbitrary, unstable display
    # order instead of Valuation/Growth/Profitability/Financial Health/
    # Momentum.
    category_averages: dict[str, float | None] = {}
    if results:
        for category in results[0].category_scores:
            scores = [
                c.score
                for r in results
                for c in r.category_scores
                if c.id == category.id and c.score is not None
            ]
            category_averages[category.id] = _mean(scores)

    sector_counts: dict[str, int] = {}
    for r in results:
        sector = r.financials.sector or "Unknown"
        sector_counts[sector] = sector_counts.get(sector, 0) + 1

    return PortfolioReview(
        portfolio_name=portfolio_name,
        holdings=tuple(results),
        failed_tickers=tuple(failed_tickers),
        overall_score=overall_score,
        tier=tier,
        category_averages=category_averages,
        sector_counts=sector_counts,
    )
