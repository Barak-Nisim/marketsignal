"""Measures how a portfolio's holdings actually moved over a tracked period.

Pure function, no I/O and no network: the caller hands in price histories
someone else already fetched, exactly like portfolio_review.py takes
already-scored holdings. That keeps the arithmetic deterministic and
unit-testable against synthetic series.

Deliberately values every holding at a fixed SHARES_PER_HOLDING shares.
MarketSignal never asks for share counts or cost basis, so a fixed
notional keeps holdings comparable and is honest about what the total
means: "what 100 shares of each of these would have done", not a real
P&L. Per-position weighting is a future enhancement, see
docs/enhancements.md.

Period windows mirror price_trend.py's calendar-days-back logic so the
report page's price chart and this table can never disagree about what
"1M" or "1Y" means. This is a record of what already happened -- there is
no projection here, and none is planned.
"""

from __future__ import annotations

import datetime as dt

from marketsignal.models import (
    HoldingPerformance,
    Portfolio,
    PortfolioPerformance,
    PortfolioValuePoint,
    PricePoint,
)

SHARES_PER_HOLDING = 100

PERIOD_LABELS = ("1M", "3M", "6M", "YTD", "1Y", "All")
DEFAULT_PERIOD = "1Y"

# calendar days to look back from the anchor date -- 1M and 1Y match
# price_trend.py exactly; YTD and All are not fixed day counts and are
# handled separately in _cutoff().
_CALENDAR_PERIODS = {"1M": 30, "3M": 91, "6M": 182, "1Y": 365}

MOVERS_SHOWN = 3  # how many best/worst movers get called out


def normalize_period(period: str) -> str:
    """Maps a user-supplied period (a CLI flag, a query string) onto one of
    PERIOD_LABELS, case-insensitively, falling back to the default rather
    than raising -- a typo in ?period= should not 500 the review page."""
    wanted = period.strip().lower()
    for label in PERIOD_LABELS:
        if label.lower() == wanted:
            return label
    return DEFAULT_PERIOD


def _cutoff(anchor: dt.date, period: str) -> dt.date | None:
    """Earliest date the window includes, or None for "All" (no cutoff)."""
    if period == "All":
        return None
    if period == "YTD":
        return dt.date(anchor.year, 1, 1)
    return anchor - dt.timedelta(days=_CALENDAR_PERIODS[period])


def _pct_change(start: float, end: float) -> float | None:
    return (end - start) / start if start else None


def build_portfolio_performance(
    portfolio: Portfolio,
    price_histories: dict[str, list[PricePoint]],
    period: str = DEFAULT_PERIOD,
) -> PortfolioPerformance:
    """Values every holding at SHARES_PER_HOLDING shares on the first and
    last trading day inside the period, and aggregates the two ends.

    A ticker with fewer than two points in the window is listed in
    excluded_tickers and left out of the totals entirely rather than
    counted as flat -- a holding we have no window for did not "not move",
    we just cannot say."""
    label = normalize_period(period)
    histories = {ticker: price_histories.get(ticker) or [] for ticker in portfolio.tickers}

    # the window is anchored on the newest close anywhere in the portfolio,
    # not on today, so the same inputs always produce the same window
    # regardless of when the function runs.
    last_dates = [h[-1].date for h in histories.values() if h]
    anchor = dt.date.fromisoformat(max(last_dates)) if last_dates else None
    cutoff = _cutoff(anchor, label) if anchor else None

    holdings: list[HoldingPerformance] = []
    excluded: list[str] = []
    windows: dict[str, list[PricePoint]] = {}

    for ticker in portfolio.tickers:
        points = [
            p
            for p in histories[ticker]
            if cutoff is None or dt.date.fromisoformat(p.date) >= cutoff
        ]
        if len(points) < 2:
            excluded.append(ticker)
            continue

        windows[ticker] = points
        start, end = points[0], points[-1]
        start_value = SHARES_PER_HOLDING * start.close
        end_value = SHARES_PER_HOLDING * end.close
        holdings.append(
            HoldingPerformance(
                ticker=ticker,
                start_date=start.date,
                end_date=end.date,
                start_price=start.close,
                end_price=end.close,
                start_value=start_value,
                end_value=end_value,
                abs_change=end_value - start_value,
                pct_change=_pct_change(start.close, end.close),
            )
        )

    start_total = sum(h.start_value for h in holdings)
    end_total = sum(h.end_value for h in holdings)

    # holdings with no percentage (a zero start price) still count toward
    # the totals but cannot be ranked, so they sort to the bottom.
    ranked = sorted(
        holdings, key=lambda h: (h.pct_change is not None, h.pct_change or 0.0), reverse=True
    )
    rankable = [h for h in ranked if h.pct_change is not None]

    return PortfolioPerformance(
        portfolio_name=portfolio.name,
        period=label,
        start_total=start_total,
        end_total=end_total,
        abs_change=end_total - start_total,
        pct_change=_pct_change(start_total, end_total),
        holdings=tuple(ranked),
        best_performers=tuple(h for h in rankable[:MOVERS_SHOWN] if h.pct_change > 0),
        worst_performers=tuple(
            h for h in reversed(rankable[-MOVERS_SHOWN:]) if h.pct_change < 0
        ),
        up_count=sum(1 for h in holdings if h.abs_change > 0),
        down_count=sum(1 for h in holdings if h.abs_change < 0),
        flat_count=sum(1 for h in holdings if h.abs_change == 0),
        excluded_tickers=tuple(excluded),
        value_series=_value_series(windows),
    )


def _value_series(windows: dict[str, list[PricePoint]]) -> tuple[PortfolioValuePoint, ...]:
    """Total portfolio value per day, restricted to dates every included
    holding traded on. Intersecting rather than forward-filling keeps the
    line from dipping on a day one ticker happened to be missing, which
    would look like a real loss."""
    if not windows:
        return ()

    closes = {ticker: {p.date: p.close for p in points} for ticker, points in windows.items()}
    shared: set[str] = set.intersection(*(set(c) for c in closes.values()))
    if len(shared) < 2:
        return ()

    return tuple(
        PortfolioValuePoint(
            date=date,
            value=sum(SHARES_PER_HOLDING * c[date] for c in closes.values()),
        )
        for date in sorted(shared)
    )
