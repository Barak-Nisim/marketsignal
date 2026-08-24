from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from marketsignal.data.yfinance_source import TickerNotFoundError, fetch_raw_financials

FAKE_INFO = {
    "longName": "Test Company Inc.",
    "sector": "Technology",
    "industry": "Software",
    "regularMarketPrice": 150.0,
    "fiftyTwoWeekLow": 100.0,
    "fiftyTwoWeekHigh": 160.0,
    "trailingPE": 22.5,
    "priceToBook": 5.0,
    "priceToSalesTrailing12Months": 4.0,
    "pegRatio": 1.2,
    "revenueGrowth": 0.15,
    "earningsGrowth": 0.12,
    "grossMargins": 0.45,
    "operatingMargins": 0.20,
    "returnOnEquity": 0.18,
    "debtToEquity": 60.0,
    "currentRatio": 1.8,
}


def _fake_history(days=365, start_price=100.0, end_price=150.0):
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days, freq="D")
    prices = [start_price + (end_price - start_price) * i / (days - 1) for i in range(days)]
    return pd.DataFrame({"Close": prices}, index=dates)


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_maps_info_fields(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = FAKE_INFO
    mock_ticker.history.return_value = _fake_history()
    mock_ticker_cls.return_value = mock_ticker

    financials = fetch_raw_financials("test")

    assert financials.ticker == "TEST"  # normalized to uppercase
    assert financials.company_name == "Test Company Inc."
    assert financials.sector == "Technology"
    assert financials.trailing_pe == 22.5
    assert financials.debt_to_equity == 60.0
    assert financials.price_change_12mo is not None
    assert financials.price_change_12mo > 0  # price rose over the fake history


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_raises_for_unknown_ticker(mock_ticker_cls):
    mock_ticker = MagicMock()
    mock_ticker.info = {}  # yfinance returns a near-empty dict for bad tickers
    mock_ticker_cls.return_value = mock_ticker

    with pytest.raises(TickerNotFoundError):
        fetch_raw_financials("BOGUS")


class _RaisingTicker:
    """A minimal stub whose .info raises, without mutating MagicMock's
    shared class the way patching a property on a MagicMock instance
    would."""

    @property
    def info(self):
        raise RuntimeError("boom")


@patch("marketsignal.data.yfinance_source.yf.Ticker")
def test_fetch_raw_financials_raises_when_yfinance_errors(mock_ticker_cls):
    mock_ticker_cls.return_value = _RaisingTicker()

    with pytest.raises(TickerNotFoundError):
        fetch_raw_financials("AAPL")


def test_price_change_handles_empty_history():
    from marketsignal.data.yfinance_source import _price_change

    assert _price_change(pd.DataFrame(), 3) is None
    assert _price_change(None, 3) is None
