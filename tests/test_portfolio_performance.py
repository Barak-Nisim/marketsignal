import datetime as dt

from marketsignal.models import Portfolio, PricePoint
from marketsignal.portfolio_performance import (
    SHARES_PER_HOLDING,
    build_portfolio_performance,
    normalize_period,
)

TODAY = dt.date(2026, 6, 30)


def _series(days: int, start_price: float, end_price: float, end: dt.date = TODAY):
    """Daily closes moving linearly from start_price to end_price, oldest
    first, ending on `end`."""
    points = []
    for i in range(days):
        date = end - dt.timedelta(days=(days - 1 - i))
        price = start_price + (end_price - start_price) * i / max(days - 1, 1)
        points.append(PricePoint(date=date.isoformat(), close=price))
    return points


def _portfolio(*tickers: str) -> Portfolio:
    return Portfolio(name="Test Portfolio", tickers=tickers)


def test_holding_that_rose_reports_gain_at_a_hundred_shares():
    histories = {"AAPL": _series(400, 100.0, 150.0)}

    perf = build_portfolio_performance(_portfolio("AAPL"), histories, "1Y")

    holding = perf.holdings[0]
    assert holding.ticker == "AAPL"
    assert holding.start_value == SHARES_PER_HOLDING * holding.start_price
    assert holding.end_value == SHARES_PER_HOLDING * holding.end_price
    assert holding.abs_change > 0
    assert holding.pct_change > 0


def test_holding_that_fell_reports_a_loss():
    histories = {"XYZ": _series(400, 150.0, 100.0)}

    perf = build_portfolio_performance(_portfolio("XYZ"), histories, "1Y")

    assert perf.holdings[0].abs_change < 0
    assert perf.holdings[0].pct_change < 0
    assert perf.direction == "down"
    assert perf.down_count == 1


def test_flat_holding_counts_as_flat_not_as_a_mover():
    histories = {"FLAT": _series(400, 100.0, 100.0)}

    perf = build_portfolio_performance(_portfolio("FLAT"), histories, "1Y")

    assert perf.holdings[0].pct_change == 0
    assert perf.flat_count == 1
    assert perf.up_count == 0 and perf.down_count == 0
    assert perf.direction == "flat"
    assert perf.best_performers == () and perf.worst_performers == ()


def test_portfolio_total_sums_both_ends_and_reports_direction():
    # 300 days of history fits entirely inside the 1Y window, so the first
    # point in the series is also the first point in the window
    histories = {
        "UP": _series(300, 100.0, 150.0),
        "DOWN": _series(300, 100.0, 90.0),
    }

    perf = build_portfolio_performance(_portfolio("UP", "DOWN"), histories, "1Y")

    assert perf.start_total == SHARES_PER_HOLDING * 200.0
    assert perf.end_total == SHARES_PER_HOLDING * 240.0
    assert perf.abs_change == SHARES_PER_HOLDING * 40.0
    assert perf.pct_change == 0.2
    assert perf.direction == "up"
    assert perf.up_count == 1 and perf.down_count == 1


def test_holdings_are_ranked_best_to_worst():
    histories = {
        "MID": _series(400, 100.0, 110.0),
        "BEST": _series(400, 100.0, 200.0),
        "WORST": _series(400, 100.0, 50.0),
    }

    perf = build_portfolio_performance(_portfolio("MID", "BEST", "WORST"), histories, "1Y")

    assert [h.ticker for h in perf.holdings] == ["BEST", "MID", "WORST"]
    assert [h.ticker for h in perf.best_performers] == ["BEST", "MID"]
    assert [h.ticker for h in perf.worst_performers] == ["WORST"]


def test_ticker_with_no_data_in_window_is_excluded_from_totals():
    histories = {
        "GOOD": _series(300, 100.0, 150.0),
        "STALE": _series(10, 50.0, 60.0, end=TODAY - dt.timedelta(days=800)),
        "EMPTY": [],
    }

    perf = build_portfolio_performance(_portfolio("GOOD", "STALE", "EMPTY"), histories, "1Y")

    assert perf.excluded_tickers == ("STALE", "EMPTY")
    assert [h.ticker for h in perf.holdings] == ["GOOD"]
    assert perf.start_total == SHARES_PER_HOLDING * 100.0


def test_single_point_in_window_is_excluded_rather_than_called_flat():
    # one close inside the window is not a measurable move, and reporting
    # it as 0% would be a claim we cannot support
    histories = {
        "THIN": [
            PricePoint(date=(TODAY - dt.timedelta(days=200)).isoformat(), close=100.0),
            PricePoint(date=TODAY.isoformat(), close=120.0),
        ]
    }

    perf = build_portfolio_performance(_portfolio("THIN"), histories, "1M")

    assert perf.excluded_tickers == ("THIN",)
    assert perf.holdings == ()
    assert perf.flat_count == 0


def test_ytd_window_starts_at_january_first_of_the_anchor_year():
    histories = {"AAPL": _series(400, 100.0, 200.0)}  # spans two calendar years

    perf = build_portfolio_performance(_portfolio("AAPL"), histories, "YTD")

    assert perf.holdings[0].start_date >= "2026-01-01"
    assert perf.holdings[0].end_date == TODAY.isoformat()


def test_all_period_uses_the_first_available_point():
    histories = {"AAPL": _series(400, 100.0, 200.0)}

    perf = build_portfolio_performance(_portfolio("AAPL"), histories, "All")

    assert perf.holdings[0].start_date == histories["AAPL"][0].date
    assert perf.holdings[0].start_price == 100.0


def test_shorter_period_sees_a_smaller_slice_than_a_longer_one():
    histories = {"AAPL": _series(400, 100.0, 200.0)}

    one_month = build_portfolio_performance(_portfolio("AAPL"), histories, "1M")
    one_year = build_portfolio_performance(_portfolio("AAPL"), histories, "1Y")

    assert one_month.holdings[0].start_date > one_year.holdings[0].start_date
    assert one_month.abs_change < one_year.abs_change


def test_empty_portfolio_returns_zeroed_totals_without_crashing():
    perf = build_portfolio_performance(_portfolio(), {}, "1Y")

    assert perf.holdings == ()
    assert perf.start_total == 0
    assert perf.end_total == 0
    assert perf.pct_change is None
    assert perf.direction == "flat"
    assert perf.value_series == ()


def test_value_series_only_covers_dates_every_holding_traded_on():
    shared = [TODAY - dt.timedelta(days=d) for d in (3, 2, 1, 0)]
    histories = {
        "A": [PricePoint(date=d.isoformat(), close=10.0) for d in shared],
        # B is missing the oldest shared date entirely
        "B": [PricePoint(date=d.isoformat(), close=20.0) for d in shared[1:]],
    }

    perf = build_portfolio_performance(_portfolio("A", "B"), histories, "1M")

    assert [p.date for p in perf.value_series] == [d.isoformat() for d in shared[1:]]
    assert perf.value_series[0].value == SHARES_PER_HOLDING * 30.0


def test_normalize_period_is_case_insensitive_and_falls_back_to_the_default():
    assert normalize_period("ytd") == "YTD"
    assert normalize_period("all") == "All"
    assert normalize_period("  1y ") == "1Y"
    assert normalize_period("nonsense") == "1Y"
