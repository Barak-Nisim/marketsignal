"""Sector-relative valuation: how a ticker's valuation metrics compare to a
typical company in its own sector, not just to fixed absolute thresholds.

scoring.py's valuation thresholds are the same across every sector -- a
trailing P/E of 30 scores identically for a bank and a software company,
even though "expensive" means something different in each. This module
adds a second, separate lens on the same four valuation metrics: how does
this ticker compare to its own sector, rather than to the market as a
whole? It never changes scoring.py's category scores or tiers -- this is
an additional view shown alongside the existing signal, not a
replacement for it.

SECTOR_VALUATION_BENCHMARKS is a static, hand-curated table of approximate
sector median multiples -- deliberately not a live peer-ticker fetch.
Fetching and averaging several peer tickers per research run would
multiply yfinance calls (and the rate-limit risk that came with it) for
every single request; a fixed table keeps this deterministic and free,
the same trade-off scoring.py already makes with its own fixed threshold
bands. These are broad, illustrative reference points, not a precise or
live feed -- expect them to drift from the real market over time and to
need periodic manual review, exactly like the threshold bands do. Sector
names match the values yfinance's `info["sector"]` actually returns
(the eleven GICS-style sectors); a ticker with an unrecognized or missing
sector (common for ETFs) simply gets no sector comparison rather than a
guessed one.
"""

from __future__ import annotations

from dataclasses import dataclass

from marketsignal.models import RawFinancials

# Approximate US-equity sector medians for the four valuation metrics.
# Illustrative reference points, not live data -- see module docstring.
SECTOR_VALUATION_BENCHMARKS: dict[str, dict[str, float]] = {
    "Technology": {
        "trailing_pe": 28.0,
        "price_to_book": 8.0,
        "price_to_sales": 6.0,
        "peg_ratio": 2.0,
    },
    "Healthcare": {
        "trailing_pe": 22.0,
        "price_to_book": 4.0,
        "price_to_sales": 3.0,
        "peg_ratio": 1.8,
    },
    "Financial Services": {
        "trailing_pe": 14.0,
        "price_to_book": 1.5,
        "price_to_sales": 3.0,
        "peg_ratio": 1.3,
    },
    "Consumer Cyclical": {
        "trailing_pe": 20.0,
        "price_to_book": 5.0,
        "price_to_sales": 1.5,
        "peg_ratio": 1.7,
    },
    "Consumer Defensive": {
        "trailing_pe": 20.0,
        "price_to_book": 5.0,
        "price_to_sales": 1.3,
        "peg_ratio": 2.2,
    },
    "Industrials": {
        "trailing_pe": 20.0,
        "price_to_book": 4.0,
        "price_to_sales": 1.8,
        "peg_ratio": 1.8,
    },
    "Energy": {
        "trailing_pe": 12.0,
        "price_to_book": 1.8,
        "price_to_sales": 1.2,
        "peg_ratio": 1.0,
    },
    "Utilities": {
        "trailing_pe": 18.0,
        "price_to_book": 2.0,
        "price_to_sales": 2.5,
        "peg_ratio": 2.5,
    },
    "Real Estate": {
        # REITs commonly show unusually high trailing P/E because
        # depreciation depresses reported earnings without reflecting
        # actual cash performance -- an approximation, not a data error.
        "trailing_pe": 35.0,
        "price_to_book": 2.0,
        "price_to_sales": 6.0,
        "peg_ratio": 2.5,
    },
    "Basic Materials": {
        "trailing_pe": 15.0,
        "price_to_book": 2.2,
        "price_to_sales": 1.3,
        "peg_ratio": 1.5,
    },
    "Communication Services": {
        "trailing_pe": 20.0,
        "price_to_book": 3.5,
        "price_to_sales": 3.0,
        "peg_ratio": 1.7,
    },
}

VALUATION_METRIC_KEYS = ("trailing_pe", "price_to_book", "price_to_sales", "peg_ratio")

_VALUATION_LABELS = {
    "trailing_pe": "Trailing P/E",
    "price_to_book": "Price / Book",
    "price_to_sales": "Price / Sales",
    "peg_ratio": "PEG Ratio",
}

# All four valuation metrics read the same way: lower means cheaper. A
# comparison ratio within this band of the sector median counts as
# "in line" rather than meaningfully cheaper or more expensive.
_IN_LINE_BAND = 0.15


@dataclass(frozen=True)
class SectorComparison:
    metric_key: str
    metric_label: str
    ticker_value: float
    sector: str
    sector_median: float
    label: str  # "Cheaper than sector" / "In line with sector" / "More expensive than sector"


def _compare_one(sector: str, metric_key: str, value: float | None) -> SectorComparison | None:
    if value is None:
        return None
    benchmarks = SECTOR_VALUATION_BENCHMARKS.get(sector)
    if benchmarks is None:
        return None
    median = benchmarks.get(metric_key)
    if median is None or median <= 0:
        return None

    ratio = value / median
    if ratio <= 1 - _IN_LINE_BAND:
        label = "Cheaper than sector"
    elif ratio >= 1 + _IN_LINE_BAND:
        label = "More expensive than sector"
    else:
        label = "In line with sector"

    return SectorComparison(
        metric_key=metric_key,
        metric_label=_VALUATION_LABELS[metric_key],
        ticker_value=value,
        sector=sector,
        sector_median=median,
        label=label,
    )


def build_valuation_sector_view(financials: RawFinancials) -> tuple[SectorComparison, ...]:
    """Compares each available valuation metric to its sector's median.

    Returns an empty tuple -- never raises -- for a ticker with no sector
    (typical for ETFs) or a sector this table doesn't recognize; the
    caller shows nothing rather than a comparison against a guess."""
    if not financials.sector:
        return ()

    comparisons = (
        _compare_one(financials.sector, key, getattr(financials, key))
        for key in VALUATION_METRIC_KEYS
    )
    return tuple(c for c in comparisons if c is not None)
