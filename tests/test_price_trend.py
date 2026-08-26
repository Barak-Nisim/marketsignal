import datetime as dt

from marketsignal.models import PricePoint
from marketsignal.price_trend import build_price_ranges


def _series(days: int, start_price: float = 100.0, end_price: float = 150.0) -> list[PricePoint]:
    today = dt.date.today()
    points = []
    for i in range(days):
        date = today - dt.timedelta(days=(days - 1 - i))
        price = start_price + (end_price - start_price) * i / max(days - 1, 1)
        points.append(PricePoint(date=date.isoformat(), close=price))
    return points


def test_build_price_ranges_empty_history_returns_nothing():
    assert build_price_ranges([]) == []


def test_build_price_ranges_returns_all_windows_for_long_history():
    ranges = build_price_ranges(_series(400))

    labels = [r.label for r in ranges]
    assert labels == ["5D", "1M", "1Y", "All"]
    for r in ranges:
        assert r.svg  # every window has enough points to render
        assert r.pct_change is not None


def test_build_price_ranges_omits_windows_without_enough_history():
    # three widely-spaced points: only the most recent one falls inside
    # the 1M cutoff, so 1M has too few points to plot even though 1Y and
    # All (which see all three) do
    today = dt.date.today()
    history = [
        PricePoint(date=(today - dt.timedelta(days=400)).isoformat(), close=100.0),
        PricePoint(date=(today - dt.timedelta(days=200)).isoformat(), close=120.0),
        PricePoint(date=today.isoformat(), close=140.0),
    ]

    ranges = build_price_ranges(history)

    labels = [r.label for r in ranges]
    assert "1M" not in labels
    assert "1Y" in labels
    assert "All" in labels


def test_build_price_ranges_single_point_returns_nothing():
    assert build_price_ranges([PricePoint(date="2026-01-01", close=100.0)]) == []


def test_build_price_ranges_pct_change_reflects_direction():
    rising = build_price_ranges(_series(400, start_price=100.0, end_price=150.0))
    falling = build_price_ranges(_series(400, start_price=150.0, end_price=100.0))

    all_rising = next(r for r in rising if r.label == "All")
    all_falling = next(r for r in falling if r.label == "All")

    assert all_rising.pct_change > 0
    assert all_falling.pct_change < 0
