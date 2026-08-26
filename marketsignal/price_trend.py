"""Builds price-history chart data for the report page's range toggle
(5D / 1M / 1Y / All), reusing the existing hand-rolled sparkline renderer
-- no new chart type, just different slices of the same daily
closing-price series, each rendered once server-side. Switching ranges
on the page is a pure CSS/JS visibility toggle between the pre-rendered
SVGs, not a new request per click.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from marketsignal.charts import sparkline_svg
from marketsignal.models import PricePoint

CHART_WIDTH = 640
CHART_HEIGHT = 160

# (label, calendar days to look back from the most recent point) -- "5D" is
# handled separately as a point count below, since daily closes already
# skip weekends/holidays and a 5-calendar-day window would often return
# fewer than 5 trading days.
_CALENDAR_RANGES = (("1M", 30), ("1Y", 365))


@dataclass(frozen=True)
class PriceRange:
    label: str
    svg: str
    pct_change: float | None


def _pct_change(points: list[PricePoint]) -> float | None:
    if len(points) < 2 or points[0].close == 0:
        return None
    return (points[-1].close - points[0].close) / points[0].close


def build_price_ranges(history: list[PricePoint]) -> list[PriceRange]:
    """One PriceRange per window (5D, 1M, 1Y, All) that has at least two
    points to plot; windows with too little history are silently omitted
    rather than shown empty (e.g. a recent IPO has no "1Y" range yet)."""
    if not history:
        return []

    last_date = dt.date.fromisoformat(history[-1].date)

    windows: list[tuple[str, list[PricePoint]]] = [("5D", history[-5:])]
    for label, days in _CALENDAR_RANGES:
        cutoff = last_date - dt.timedelta(days=days)
        windows.append((label, [p for p in history if dt.date.fromisoformat(p.date) >= cutoff]))
    windows.append(("All", history))

    ranges: list[PriceRange] = []
    for label, points in windows:
        if len(points) < 2:
            continue
        svg = sparkline_svg([p.close for p in points], width=CHART_WIDTH, height=CHART_HEIGHT)
        if not svg:
            continue
        ranges.append(PriceRange(label=label, svg=svg, pct_change=_pct_change(points)))

    return ranges
